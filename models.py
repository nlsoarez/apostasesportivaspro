"""
Database models for predictions tracking and learning
"""
from datetime import datetime
from sqlalchemy import Column, Integer, Float, String, Boolean, DateTime, JSON, Text, Index
from database import Base


class Prediction(Base):
    """
    Armazena todas as predições feitas pelo sistema
    """
    __tablename__ = 'predictions'

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Identificação da partida e tipo de predição
    fixture_id = Column(Integer, nullable=False, index=True)
    league_id = Column(Integer, nullable=True)
    season = Column(Integer, nullable=True)
    prediction_type = Column(String(50), nullable=False, index=True)  # 'corners', 'cards', 'value', 'goals', etc

    # Detalhes da predição
    prediction_value = Column(Float, nullable=True)  # Ex: 10.5 escanteios
    prediction_line = Column(String(20), nullable=True)  # Ex: "Over", "Under", "Yes", "No"
    recommended_bet = Column(Text, nullable=True)  # Descrição legível da aposta recomendada
    confidence = Column(Float, nullable=True)  # 0.0 a 1.0

    # Contexto Must Win
    must_win_home = Column(Float, nullable=True)
    must_win_away = Column(Float, nullable=True)
    must_win_home_level = Column(String(20), nullable=True)  # 'CRITICAL', 'HIGH', 'MODERATE', 'LOW'
    must_win_away_level = Column(String(20), nullable=True)

    # Odds (se disponível)
    odds_value = Column(Float, nullable=True)
    expected_value = Column(Float, nullable=True)  # (probability * odd) - 1

    # Metadata adicional (estatísticas, contexto, etc)
    prediction_metadata = Column(JSON, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    fixture_date = Column(DateTime, nullable=True)  # Data/hora da partida

    # Verificação de resultado
    verified = Column(Boolean, default=False, nullable=False, index=True)
    actual_result = Column(Float, nullable=True)  # Resultado real (ex: 12 escanteios)
    was_correct = Column(Boolean, nullable=True)  # A predição estava correta?
    profit_loss = Column(Float, nullable=True)  # Lucro/prejuízo se apostado 1 unidade
    verified_at = Column(DateTime, nullable=True)

    # Índices compostos para queries comuns
    __table_args__ = (
        Index('idx_fixture_type', 'fixture_id', 'prediction_type'),
        Index('idx_verified_type', 'verified', 'prediction_type'),
        Index('idx_created_verified', 'created_at', 'verified'),
    )

    def __repr__(self):
        return f"<Prediction(id={self.id}, fixture={self.fixture_id}, type={self.prediction_type}, value={self.prediction_value}, correct={self.was_correct})>"

    def to_dict(self):
        """Converte para dicionário (útil para JSON responses)"""
        return {
            'id': self.id,
            'fixture_id': self.fixture_id,
            'league_id': self.league_id,
            'season': self.season,
            'prediction_type': self.prediction_type,
            'prediction_value': self.prediction_value,
            'prediction_line': self.prediction_line,
            'recommended_bet': self.recommended_bet,
            'confidence': self.confidence,
            'must_win_home': self.must_win_home,
            'must_win_away': self.must_win_away,
            'must_win_home_level': self.must_win_home_level,
            'must_win_away_level': self.must_win_away_level,
            'odds_value': self.odds_value,
            'expected_value': self.expected_value,
            'metadata': self.prediction_metadata,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'fixture_date': self.fixture_date.isoformat() if self.fixture_date else None,
            'verified': self.verified,
            'actual_result': self.actual_result,
            'was_correct': self.was_correct,
            'profit_loss': self.profit_loss,
            'verified_at': self.verified_at.isoformat() if self.verified_at else None
        }


class PerformanceMetrics(Base):
    """
    Métricas agregadas de performance por período
    """
    __tablename__ = 'performance_metrics'

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Tipo de predição e período
    prediction_type = Column(String(50), nullable=False, index=True)
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)

    # Métricas de volume
    total_predictions = Column(Integer, default=0)
    total_verified = Column(Integer, default=0)
    total_pending = Column(Integer, default=0)

    # Métricas de acurácia
    total_correct = Column(Integer, default=0)
    total_incorrect = Column(Integer, default=0)
    accuracy_rate = Column(Float, nullable=True)  # correct / verified

    # Métricas de confiança
    avg_confidence = Column(Float, nullable=True)
    confidence_calibration = Column(JSON, nullable=True)  # {range: {predicted: X, actual: Y}}

    # Métricas financeiras
    total_profit_loss = Column(Float, default=0.0)
    roi = Column(Float, nullable=True)  # Return on Investment
    sharpe_ratio = Column(Float, nullable=True)  # Risk-adjusted return

    # Métricas por Must Win level
    metrics_by_must_win = Column(JSON, nullable=True)  # {'CRITICAL': {...}, 'HIGH': {...}}

    # Metadata
    metrics_metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index('idx_type_period', 'prediction_type', 'period_start', 'period_end'),
    )

    def __repr__(self):
        return f"<PerformanceMetrics(type={self.prediction_type}, accuracy={self.accuracy_rate}, roi={self.roi})>"

    def to_dict(self):
        return {
            'id': self.id,
            'prediction_type': self.prediction_type,
            'period_start': self.period_start.isoformat() if self.period_start else None,
            'period_end': self.period_end.isoformat() if self.period_end else None,
            'total_predictions': self.total_predictions,
            'total_verified': self.total_verified,
            'total_pending': self.total_pending,
            'total_correct': self.total_correct,
            'total_incorrect': self.total_incorrect,
            'accuracy_rate': self.accuracy_rate,
            'avg_confidence': self.avg_confidence,
            'confidence_calibration': self.confidence_calibration,
            'total_profit_loss': self.total_profit_loss,
            'roi': self.roi,
            'sharpe_ratio': self.sharpe_ratio,
            'metrics_by_must_win': self.metrics_by_must_win,
            'metadata': self.metrics_metadata,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class ModelParameters(Base):
    """
    Parâmetros do modelo para tracking e otimização
    """
    __tablename__ = 'model_parameters'

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Identificação do parâmetro
    parameter_name = Column(String(100), nullable=False, index=True)
    parameter_group = Column(String(50), nullable=True)  # Ex: 'must_win_weights', 'adjustment_factors'
    parameter_value = Column(Float, nullable=False)
    parameter_type = Column(String(20), default='float')  # 'float', 'int', 'bool'

    # Versionamento
    version = Column(Integer, default=1)
    is_active = Column(Boolean, default=True, index=True)

    # Validade temporal
    valid_from = Column(DateTime, default=datetime.utcnow, nullable=False)
    valid_to = Column(DateTime, nullable=True)

    # Performance tracking
    performance_impact = Column(Float, nullable=True)  # Impacto na acurácia (ex: +0.05 = +5%)
    tested_on_predictions = Column(Integer, default=0)

    # Metadata
    description = Column(Text, nullable=True)
    parameter_metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(String(50), default='system')

    __table_args__ = (
        Index('idx_param_active', 'parameter_name', 'is_active'),
    )

    def __repr__(self):
        return f"<ModelParameters(name={self.parameter_name}, value={self.parameter_value}, active={self.is_active})>"

    def to_dict(self):
        return {
            'id': self.id,
            'parameter_name': self.parameter_name,
            'parameter_group': self.parameter_group,
            'parameter_value': self.parameter_value,
            'parameter_type': self.parameter_type,
            'version': self.version,
            'is_active': self.is_active,
            'valid_from': self.valid_from.isoformat() if self.valid_from else None,
            'valid_to': self.valid_to.isoformat() if self.valid_to else None,
            'performance_impact': self.performance_impact,
            'tested_on_predictions': self.tested_on_predictions,
            'description': self.description,
            'metadata': self.parameter_metadata,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'created_by': self.created_by
        }


class LearningInsights(Base):
    """
    Insights e padrões descobertos pelo sistema
    """
    __tablename__ = 'learning_insights'

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Tipo e conteúdo do insight
    insight_type = Column(String(50), nullable=False, index=True)  # 'pattern', 'recommendation', 'alert'
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)

    # Relevância e confiança
    confidence = Column(Float, nullable=True)  # Quão confiável é este insight (0-1)
    impact = Column(String(20), nullable=True)  # 'high', 'medium', 'low'
    priority = Column(Integer, default=0)  # Para ordenação

    # Contexto
    prediction_type = Column(String(50), nullable=True)
    league_id = Column(Integer, nullable=True)
    must_win_level = Column(String(20), nullable=True)

    # Dados suportando o insight
    supporting_data = Column(JSON, nullable=True)
    sample_size = Column(Integer, nullable=True)  # Quantas predições suportam este insight

    # Status
    is_active = Column(Boolean, default=True)
    is_actionable = Column(Boolean, default=True)
    action_taken = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    expires_at = Column(DateTime, nullable=True)  # Alguns insights podem expirar

    def __repr__(self):
        return f"<LearningInsights(type={self.insight_type}, title={self.title}, impact={self.impact})>"

    def to_dict(self):
        return {
            'id': self.id,
            'insight_type': self.insight_type,
            'title': self.title,
            'description': self.description,
            'confidence': self.confidence,
            'impact': self.impact,
            'priority': self.priority,
            'prediction_type': self.prediction_type,
            'league_id': self.league_id,
            'must_win_level': self.must_win_level,
            'supporting_data': self.supporting_data,
            'sample_size': self.sample_size,
            'is_active': self.is_active,
            'is_actionable': self.is_actionable,
            'action_taken': self.action_taken,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None
        }
