"""
Learning service - Business logic for prediction tracking and learning
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
from sqlalchemy import func, and_, or_, case
from sqlalchemy.orm import Session

from models import Prediction, PerformanceMetrics, ModelParameters, LearningInsights


class LearningService:
    """
    Serviço para gerenciar aprendizado e feedback do sistema
    """

    @staticmethod
    def save_prediction(
        db: Session,
        fixture_id: int,
        prediction_type: str,
        prediction_value: Optional[float] = None,
        prediction_line: Optional[str] = None,
        recommended_bet: Optional[str] = None,
        confidence: Optional[float] = None,
        must_win_home: Optional[float] = None,
        must_win_away: Optional[float] = None,
        must_win_home_level: Optional[str] = None,
        must_win_away_level: Optional[str] = None,
        odds_value: Optional[float] = None,
        expected_value: Optional[float] = None,
        league_id: Optional[int] = None,
        season: Optional[int] = None,
        fixture_date: Optional[datetime] = None,
        metadata: Optional[Dict] = None
    ) -> Prediction:
        """
        Salva uma nova predição no banco de dados
        """
        prediction = Prediction(
            fixture_id=fixture_id,
            league_id=league_id,
            season=season,
            prediction_type=prediction_type,
            prediction_value=prediction_value,
            prediction_line=prediction_line,
            recommended_bet=recommended_bet,
            confidence=confidence,
            must_win_home=must_win_home,
            must_win_away=must_win_away,
            must_win_home_level=must_win_home_level,
            must_win_away_level=must_win_away_level,
            odds_value=odds_value,
            expected_value=expected_value,
            fixture_date=fixture_date,
            prediction_metadata=metadata
        )

        db.add(prediction)
        db.commit()
        db.refresh(prediction)

        return prediction

    @staticmethod
    def verify_prediction(
        db: Session,
        prediction_id: int,
        actual_result: float,
        stake: float = 1.0
    ) -> Prediction:
        """
        Verifica uma predição com o resultado real
        """
        prediction = db.query(Prediction).filter(Prediction.id == prediction_id).first()

        if not prediction:
            raise ValueError(f"Prediction {prediction_id} not found")

        if prediction.verified:
            raise ValueError(f"Prediction {prediction_id} already verified")

        # Determinar se estava correta
        was_correct = LearningService._check_prediction_correctness(
            prediction.prediction_value,
            prediction.prediction_line,
            actual_result
        )

        # Calcular lucro/prejuízo
        profit_loss = 0.0
        if prediction.odds_value:
            if was_correct:
                profit_loss = stake * (prediction.odds_value - 1)
            else:
                profit_loss = -stake

        # Atualizar predição
        prediction.verified = True
        prediction.actual_result = actual_result
        prediction.was_correct = was_correct
        prediction.profit_loss = profit_loss
        prediction.verified_at = datetime.utcnow()

        db.commit()
        db.refresh(prediction)

        return prediction

    @staticmethod
    def verify_predictions_by_fixture(
        db: Session,
        fixture_id: int,
        actual_results: Dict[str, float]
    ) -> List[Prediction]:
        """
        Verifica múltiplas predições de uma partida de uma vez

        Args:
            fixture_id: ID da partida
            actual_results: Dict com resultados reais, ex:
                {
                    'corners': 12.0,
                    'cards': 5.0,
                    'goals': 3.0
                }
        """
        predictions = db.query(Prediction).filter(
            and_(
                Prediction.fixture_id == fixture_id,
                Prediction.verified == False
            )
        ).all()

        verified = []
        for prediction in predictions:
            if prediction.prediction_type in actual_results:
                actual = actual_results[prediction.prediction_type]
                try:
                    verified_pred = LearningService.verify_prediction(
                        db, prediction.id, actual
                    )
                    verified.append(verified_pred)
                except ValueError:
                    continue

        return verified

    @staticmethod
    def _check_prediction_correctness(
        prediction_value: Optional[float],
        prediction_line: Optional[str],
        actual_result: float
    ) -> bool:
        """
        Determina se uma predição estava correta
        """
        if prediction_value is None:
            return False

        if prediction_line:
            line_upper = prediction_line.upper()
            if line_upper in ['OVER', 'MAIS', 'ACIMA']:
                return actual_result > prediction_value
            elif line_upper in ['UNDER', 'MENOS', 'ABAIXO']:
                return actual_result < prediction_value
            elif line_upper in ['YES', 'SIM']:
                return actual_result >= prediction_value
            elif line_upper in ['NO', 'NAO', 'NÃO']:
                return actual_result < prediction_value

        # Se não tem linha, considera correto se próximo (margem de 10%)
        margin = prediction_value * 0.1
        return abs(actual_result - prediction_value) <= margin

    @staticmethod
    def get_prediction_metrics(
        db: Session,
        prediction_type: Optional[str] = None,
        days: int = 30,
        must_win_level: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Calcula métricas de performance das predições
        """
        since = datetime.utcnow() - timedelta(days=days)

        # Query base
        query = db.query(Prediction).filter(Prediction.created_at >= since)

        if prediction_type:
            query = query.filter(Prediction.prediction_type == prediction_type)

        if must_win_level:
            query = query.filter(
                or_(
                    Prediction.must_win_home_level == must_win_level,
                    Prediction.must_win_away_level == must_win_level
                )
            )

        # Estatísticas gerais
        all_predictions = query.all()
        verified_predictions = [p for p in all_predictions if p.verified]

        total = len(all_predictions)
        verified_count = len(verified_predictions)
        correct = len([p for p in verified_predictions if p.was_correct])
        incorrect = verified_count - correct

        accuracy = correct / verified_count if verified_count > 0 else 0.0

        # Métricas financeiras
        total_profit_loss = sum(p.profit_loss or 0 for p in verified_predictions)
        roi = (total_profit_loss / verified_count) if verified_count > 0 else 0.0

        # Confiança média
        avg_confidence = sum(p.confidence or 0 for p in verified_predictions) / verified_count if verified_count > 0 else 0.0

        # Calibração de confiança (binned)
        confidence_bins = {
            '0-50%': {'predicted': 0, 'actual': 0, 'count': 0},
            '50-60%': {'predicted': 0, 'actual': 0, 'count': 0},
            '60-70%': {'predicted': 0, 'actual': 0, 'count': 0},
            '70-80%': {'predicted': 0, 'actual': 0, 'count': 0},
            '80-90%': {'predicted': 0, 'actual': 0, 'count': 0},
            '90-100%': {'predicted': 0, 'actual': 0, 'count': 0},
        }

        for pred in verified_predictions:
            if pred.confidence is None:
                continue

            conf = pred.confidence
            if conf < 0.5:
                bin_key = '0-50%'
            elif conf < 0.6:
                bin_key = '50-60%'
            elif conf < 0.7:
                bin_key = '60-70%'
            elif conf < 0.8:
                bin_key = '70-80%'
            elif conf < 0.9:
                bin_key = '80-90%'
            else:
                bin_key = '90-100%'

            confidence_bins[bin_key]['predicted'] += conf
            confidence_bins[bin_key]['actual'] += (1 if pred.was_correct else 0)
            confidence_bins[bin_key]['count'] += 1

        # Calcular médias nos bins
        for bin_key, bin_data in confidence_bins.items():
            if bin_data['count'] > 0:
                bin_data['predicted'] = bin_data['predicted'] / bin_data['count']
                bin_data['actual'] = bin_data['actual'] / bin_data['count']

        # Métricas por Must Win level
        must_win_metrics = {}
        for level in ['CRITICAL', 'HIGH', 'MODERATE', 'LOW']:
            level_preds = [p for p in verified_predictions
                          if p.must_win_home_level == level or p.must_win_away_level == level]
            if level_preds:
                level_correct = len([p for p in level_preds if p.was_correct])
                must_win_metrics[level] = {
                    'count': len(level_preds),
                    'accuracy': level_correct / len(level_preds),
                    'avg_confidence': sum(p.confidence or 0 for p in level_preds) / len(level_preds)
                }

        return {
            'period': {
                'days': days,
                'since': since.isoformat(),
                'until': datetime.utcnow().isoformat()
            },
            'filters': {
                'prediction_type': prediction_type,
                'must_win_level': must_win_level
            },
            'volume': {
                'total_predictions': total,
                'verified': verified_count,
                'pending': total - verified_count
            },
            'accuracy': {
                'correct': correct,
                'incorrect': incorrect,
                'accuracy_rate': accuracy
            },
            'confidence': {
                'average': avg_confidence,
                'calibration': {k: v for k, v in confidence_bins.items() if v['count'] > 0}
            },
            'financial': {
                'total_profit_loss': total_profit_loss,
                'roi': roi,
                'roi_percentage': roi * 100
            },
            'by_must_win_level': must_win_metrics
        }

    @staticmethod
    def get_dashboard_data(db: Session, days: int = 30) -> Dict[str, Any]:
        """
        Retorna dados consolidados para dashboard
        """
        overall_metrics = LearningService.get_prediction_metrics(db, days=days)

        # Métricas por tipo
        by_type = {}
        for pred_type in ['corners', 'cards', 'value', 'goals']:
            metrics = LearningService.get_prediction_metrics(
                db, prediction_type=pred_type, days=days
            )
            if metrics['volume']['total_predictions'] > 0:
                by_type[pred_type] = {
                    'accuracy': metrics['accuracy']['accuracy_rate'],
                    'roi': metrics['financial']['roi'],
                    'count': metrics['volume']['verified'],
                    'avg_confidence': metrics['confidence']['average']
                }

        # Top insights recentes
        insights = db.query(LearningInsights).filter(
            and_(
                LearningInsights.is_active == True,
                or_(
                    LearningInsights.expires_at == None,
                    LearningInsights.expires_at > datetime.utcnow()
                )
            )
        ).order_by(
            LearningInsights.priority.desc(),
            LearningInsights.created_at.desc()
        ).limit(10).all()

        # Recomendações automáticas
        recommendations = LearningService._generate_recommendations(by_type, overall_metrics)

        return {
            'overall': overall_metrics,
            'by_type': by_type,
            'insights': [i.to_dict() for i in insights],
            'recommendations': recommendations,
            'generated_at': datetime.utcnow().isoformat()
        }

    @staticmethod
    def _generate_recommendations(by_type: Dict, overall: Dict) -> List[Dict[str, str]]:
        """
        Gera recomendações baseadas nas métricas
        """
        recommendations = []

        # Verificar qual método tem melhor performance
        if by_type:
            best_type = max(by_type.items(), key=lambda x: x[1].get('roi', -999))
            worst_type = min(by_type.items(), key=lambda x: x[1].get('roi', 999))

            if best_type[1]['roi'] > 0.05:
                recommendations.append({
                    'type': 'success',
                    'message': f"Método '{best_type[0]}' tem excelente performance (ROI: {best_type[1]['roi']*100:.1f}%) - priorizar este tipo de análise"
                })

            if worst_type[1]['roi'] < -0.02 and worst_type[1]['count'] > 10:
                recommendations.append({
                    'type': 'warning',
                    'message': f"Método '{worst_type[0]}' com ROI negativo ({worst_type[1]['roi']*100:.1f}%) - revisar fórmulas ou evitar"
                })

        # Verificar acurácia geral
        accuracy = overall['accuracy']['accuracy_rate']
        if accuracy > 0.65:
            recommendations.append({
                'type': 'success',
                'message': f"Acurácia geral excelente ({accuracy*100:.1f}%) - sistema está bem calibrado"
            })
        elif accuracy < 0.50 and overall['volume']['verified'] > 20:
            recommendations.append({
                'type': 'alert',
                'message': f"Acurácia baixa ({accuracy*100:.1f}%) - revisar parâmetros urgentemente"
            })

        # Verificar calibração de confiança
        calibration = overall['confidence'].get('calibration', {})
        for bin_range, data in calibration.items():
            if data['count'] >= 10:  # Sample size mínimo
                predicted = data['predicted']
                actual = data['actual']
                diff = abs(predicted - actual)

                if diff > 0.15:  # 15% de diferença
                    if predicted > actual:
                        recommendations.append({
                            'type': 'warning',
                            'message': f"Confiança sobre-estimada na faixa {bin_range} (previsto {predicted*100:.0f}%, real {actual*100:.0f}%)"
                        })
                    else:
                        recommendations.append({
                            'type': 'info',
                            'message': f"Confiança subestimada na faixa {bin_range} - podemos ser mais confiantes"
                        })

        # Verificar volume de verificações
        verified_pct = overall['volume']['verified'] / overall['volume']['total_predictions'] if overall['volume']['total_predictions'] > 0 else 0
        if verified_pct < 0.5 and overall['volume']['total_predictions'] > 20:
            recommendations.append({
                'type': 'info',
                'message': f"Apenas {verified_pct*100:.0f}% das predições foram verificadas - aumentar taxa de verificação para melhor aprendizado"
            })

        return recommendations

    @staticmethod
    def create_insight(
        db: Session,
        insight_type: str,
        title: str,
        description: str,
        confidence: Optional[float] = None,
        impact: Optional[str] = None,
        prediction_type: Optional[str] = None,
        supporting_data: Optional[Dict] = None,
        sample_size: Optional[int] = None,
        expires_in_days: Optional[int] = None
    ) -> LearningInsights:
        """
        Cria um novo insight de aprendizado
        """
        expires_at = None
        if expires_in_days:
            expires_at = datetime.utcnow() + timedelta(days=expires_in_days)

        insight = LearningInsights(
            insight_type=insight_type,
            title=title,
            description=description,
            confidence=confidence,
            impact=impact,
            prediction_type=prediction_type,
            supporting_data=supporting_data,
            sample_size=sample_size,
            expires_at=expires_at
        )

        db.add(insight)
        db.commit()
        db.refresh(insight)

        return insight
