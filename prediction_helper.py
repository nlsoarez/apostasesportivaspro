"""
Helper functions to automatically save predictions from analysis endpoints
"""
from typing import Optional, Dict, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Flag para habilitar/desabilitar auto-save
AUTO_SAVE_ENABLED = True


def auto_save_prediction(
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
) -> Optional[Dict[str, Any]]:
    """
    Salva automaticamente uma predição no banco de dados
    Se o sistema de learning não estiver disponível, retorna None silenciosamente

    Returns:
        Dict com dados da predição salva, ou None se não foi possível salvar
    """
    if not AUTO_SAVE_ENABLED:
        return None

    try:
        from database import db_session
        from learning_service import LearningService

        prediction = LearningService.save_prediction(
            db=db_session,
            fixture_id=fixture_id,
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
            league_id=league_id,
            season=season,
            fixture_date=fixture_date,
            metadata=metadata  # será mapeado para prediction_metadata internamente
        )

        logger.info(f"📊 Auto-saved prediction: {prediction_type} for fixture {fixture_id} (ID: {prediction.id})")
        return prediction.to_dict()

    except ImportError:
        # Learning system não instalado - ignorar silenciosamente
        return None
    except Exception as e:
        # Erro ao salvar - log mas não quebrar a request
        logger.warning(f"⚠️  Failed to auto-save prediction: {e}")
        return None


def parse_must_win_level(score: float) -> str:
    """
    Converte score Must Win (0-10) para nível categórico
    """
    if score >= 8.0:
        return "CRITICAL"
    elif score >= 6.5:
        return "HIGH"
    elif score >= 5.0:
        return "MODERATE"
    else:
        return "LOW"


def extract_fixture_metadata(fixture_data: Dict) -> Dict[str, Any]:
    """
    Extrai metadados úteis de um fixture para salvar com a predição
    """
    try:
        metadata = {
            "teams": {
                "home": fixture_data.get("teams", {}).get("home", {}).get("name"),
                "away": fixture_data.get("teams", {}).get("away", {}).get("name")
            },
            "league": {
                "id": fixture_data.get("league", {}).get("id"),
                "name": fixture_data.get("league", {}).get("name"),
                "country": fixture_data.get("league", {}).get("country")
            },
            "fixture": {
                "date": fixture_data.get("fixture", {}).get("date"),
                "venue": fixture_data.get("fixture", {}).get("venue", {}).get("name"),
                "status": fixture_data.get("fixture", {}).get("status", {}).get("short")
            }
        }
        return metadata
    except Exception:
        return {}


def calculate_expected_value(probability: float, odds: float) -> float:
    """
    Calcula Expected Value (Kelly Criterion)
    EV = (probability × odds) - 1
    """
    if probability <= 0 or probability > 1:
        return 0.0
    if odds < 1.0:
        return 0.0

    return (probability * odds) - 1.0


def format_prediction_line(recommendation: str) -> Optional[str]:
    """
    Extrai a linha de predição (Over/Under/Yes/No) da recomendação
    """
    rec_upper = recommendation.upper()

    if "OVER" in rec_upper or "ACIMA" in rec_upper or "MAIS" in rec_upper:
        return "Over"
    elif "UNDER" in rec_upper or "ABAIXO" in rec_upper or "MENOS" in rec_upper:
        return "Under"
    elif any(word in rec_upper for word in ["SIM", "YES", "AMBOS", "BOTH"]):
        return "Yes"
    elif any(word in rec_upper for word in ["NAO", "NÃO", "NO"]):
        return "No"

    return None


# Exemplo de uso em endpoints de análise:
"""
# No endpoint de análise de escanteios:

@app.route("/analysis/corners")
def analyze_corners():
    # ... fazer análise ...

    # Auto-salvar predição
    auto_save_prediction(
        fixture_id=fixture_id,
        prediction_type="corners",
        prediction_value=estimativa_final,
        prediction_line=format_prediction_line(recomendacao),
        recommended_bet=recomendacao,
        confidence=confianca_ajustada,
        must_win_home=must_win_home_score,
        must_win_away=must_win_away_score,
        must_win_home_level=parse_must_win_level(must_win_home_score),
        must_win_away_level=parse_must_win_level(must_win_away_score),
        league_id=league_id,
        season=season,
        metadata=extract_fixture_metadata(fixture_data)
    )

    # ... retornar resposta normalmente ...
"""
