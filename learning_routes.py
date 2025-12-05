"""
Learning and feedback API routes
"""
from flask import Blueprint, jsonify, request
from datetime import datetime
from typing import Optional

from database import db_session
from learning_service import LearningService
from models import Prediction, LearningInsights

# Criar blueprint
learning_bp = Blueprint('learning', __name__, url_prefix='/predictions')


@learning_bp.route('/save', methods=['POST'])
def save_prediction():
    """
    Salva uma nova predição no sistema

    Body JSON:
    {
        "fixture_id": 12345,
        "prediction_type": "corners",
        "prediction_value": 10.5,
        "prediction_line": "Over",
        "recommended_bet": "Over 10.5 escanteios",
        "confidence": 0.72,
        "must_win_home": 6.5,
        "must_win_away": 3.0,
        "must_win_home_level": "HIGH",
        "must_win_away_level": "LOW",
        "odds_value": 1.85,
        "expected_value": 0.33,
        "league_id": 71,
        "season": 2025,
        "fixture_date": "2025-12-06T20:00:00",
        "metadata": {...}
    }
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({"ok": False, "error": "Request body required"}), 400

        # Validações
        if 'fixture_id' not in data:
            return jsonify({"ok": False, "error": "fixture_id is required"}), 400
        if 'prediction_type' not in data:
            return jsonify({"ok": False, "error": "prediction_type is required"}), 400

        # Parse fixture_date se fornecido
        fixture_date = None
        if 'fixture_date' in data and data['fixture_date']:
            try:
                fixture_date = datetime.fromisoformat(data['fixture_date'].replace('Z', '+00:00'))
            except ValueError:
                return jsonify({"ok": False, "error": "Invalid fixture_date format"}), 400

        # Salvar predição
        prediction = LearningService.save_prediction(
            db=db_session,
            fixture_id=data['fixture_id'],
            prediction_type=data['prediction_type'],
            prediction_value=data.get('prediction_value'),
            prediction_line=data.get('prediction_line'),
            recommended_bet=data.get('recommended_bet'),
            confidence=data.get('confidence'),
            must_win_home=data.get('must_win_home'),
            must_win_away=data.get('must_win_away'),
            must_win_home_level=data.get('must_win_home_level'),
            must_win_away_level=data.get('must_win_away_level'),
            odds_value=data.get('odds_value'),
            expected_value=data.get('expected_value'),
            league_id=data.get('league_id'),
            season=data.get('season'),
            fixture_date=fixture_date,
            metadata=data.get('metadata')  # será mapeado para prediction_metadata
        )

        return jsonify({
            "ok": True,
            "message": "Prediction saved successfully",
            "data": prediction.to_dict()
        }), 201

    except Exception as e:
        db_session.rollback()
        return jsonify({
            "ok": False,
            "error": f"Error saving prediction: {str(e)}"
        }), 500


@learning_bp.route('/verify/<int:prediction_id>', methods=['POST'])
def verify_prediction(prediction_id: int):
    """
    Verifica uma predição com o resultado real

    Body JSON:
    {
        "actual_result": 12.0,
        "stake": 1.0
    }
    """
    try:
        data = request.get_json()

        if not data or 'actual_result' not in data:
            return jsonify({"ok": False, "error": "actual_result is required"}), 400

        actual_result = float(data['actual_result'])
        stake = float(data.get('stake', 1.0))

        prediction = LearningService.verify_prediction(
            db=db_session,
            prediction_id=prediction_id,
            actual_result=actual_result,
            stake=stake
        )

        return jsonify({
            "ok": True,
            "message": "Prediction verified successfully",
            "data": prediction.to_dict()
        }), 200

    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 404
    except Exception as e:
        db_session.rollback()
        return jsonify({
            "ok": False,
            "error": f"Error verifying prediction: {str(e)}"
        }), 500


@learning_bp.route('/verify-fixture/<int:fixture_id>', methods=['POST'])
def verify_fixture(fixture_id: int):
    """
    Verifica todas as predições de uma partida de uma vez

    Body JSON:
    {
        "corners": 12.0,
        "cards": 5.0,
        "goals": 3.0
    }
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({"ok": False, "error": "Results data required"}), 400

        predictions = LearningService.verify_predictions_by_fixture(
            db=db_session,
            fixture_id=fixture_id,
            actual_results=data
        )

        return jsonify({
            "ok": True,
            "message": f"Verified {len(predictions)} predictions",
            "data": [p.to_dict() for p in predictions]
        }), 200

    except Exception as e:
        db_session.rollback()
        return jsonify({
            "ok": False,
            "error": f"Error verifying fixture predictions: {str(e)}"
        }), 500


@learning_bp.route('/metrics', methods=['GET'])
def get_metrics():
    """
    Retorna métricas de performance

    Query params:
    - type: tipo de predição (corners, cards, etc)
    - days: período em dias (default: 30)
    - must_win_level: filtrar por nível de Must Win
    """
    try:
        prediction_type = request.args.get('type')
        days = int(request.args.get('days', 30))
        must_win_level = request.args.get('must_win_level')

        if days < 1 or days > 365:
            return jsonify({"ok": False, "error": "days must be between 1 and 365"}), 400

        metrics = LearningService.get_prediction_metrics(
            db=db_session,
            prediction_type=prediction_type,
            days=days,
            must_win_level=must_win_level
        )

        return jsonify({
            "ok": True,
            "data": metrics
        }), 200

    except Exception as e:
        return jsonify({
            "ok": False,
            "error": f"Error calculating metrics: {str(e)}"
        }), 500


@learning_bp.route('/dashboard', methods=['GET'])
def get_dashboard():
    """
    Retorna dados consolidados para dashboard

    Query params:
    - days: período em dias (default: 30)
    """
    try:
        days = int(request.args.get('days', 30))

        if days < 1 or days > 365:
            return jsonify({"ok": False, "error": "days must be between 1 and 365"}), 400

        dashboard = LearningService.get_dashboard_data(
            db=db_session,
            days=days
        )

        return jsonify({
            "ok": True,
            "data": dashboard
        }), 200

    except Exception as e:
        return jsonify({
            "ok": False,
            "error": f"Error generating dashboard: {str(e)}"
        }), 500


@learning_bp.route('/list', methods=['GET'])
def list_predictions():
    """
    Lista predições com filtros

    Query params:
    - fixture_id: filtrar por partida
    - type: tipo de predição
    - verified: true/false
    - limit: número máximo de resultados (default: 50)
    - offset: skip de resultados (default: 0)
    """
    try:
        fixture_id = request.args.get('fixture_id', type=int)
        prediction_type = request.args.get('type')
        verified = request.args.get('verified')
        limit = min(int(request.args.get('limit', 50)), 200)
        offset = int(request.args.get('offset', 0))

        query = db_session.query(Prediction)

        if fixture_id:
            query = query.filter(Prediction.fixture_id == fixture_id)
        if prediction_type:
            query = query.filter(Prediction.prediction_type == prediction_type)
        if verified is not None:
            verified_bool = verified.lower() in ['true', '1', 'yes']
            query = query.filter(Prediction.verified == verified_bool)

        total = query.count()
        predictions = query.order_by(
            Prediction.created_at.desc()
        ).limit(limit).offset(offset).all()

        return jsonify({
            "ok": True,
            "data": {
                "predictions": [p.to_dict() for p in predictions],
                "total": total,
                "limit": limit,
                "offset": offset
            }
        }), 200

    except Exception as e:
        return jsonify({
            "ok": False,
            "error": f"Error listing predictions: {str(e)}"
        }), 500


@learning_bp.route('/<int:prediction_id>', methods=['GET'])
def get_prediction(prediction_id: int):
    """
    Retorna uma predição específica
    """
    try:
        prediction = db_session.query(Prediction).filter(
            Prediction.id == prediction_id
        ).first()

        if not prediction:
            return jsonify({"ok": False, "error": "Prediction not found"}), 404

        return jsonify({
            "ok": True,
            "data": prediction.to_dict()
        }), 200

    except Exception as e:
        return jsonify({
            "ok": False,
            "error": f"Error fetching prediction: {str(e)}"
        }), 500


@learning_bp.route('/insights', methods=['GET'])
def get_insights():
    """
    Retorna insights de aprendizado

    Query params:
    - type: tipo de insight
    - active: true/false
    - limit: número máximo de resultados (default: 20)
    """
    try:
        insight_type = request.args.get('type')
        active = request.args.get('active')
        limit = min(int(request.args.get('limit', 20)), 100)

        query = db_session.query(LearningInsights)

        if insight_type:
            query = query.filter(LearningInsights.insight_type == insight_type)

        if active is not None:
            active_bool = active.lower() in ['true', '1', 'yes']
            query = query.filter(LearningInsights.is_active == active_bool)

        # Filtrar expirados
        query = query.filter(
            (LearningInsights.expires_at == None) |
            (LearningInsights.expires_at > datetime.utcnow())
        )

        insights = query.order_by(
            LearningInsights.priority.desc(),
            LearningInsights.created_at.desc()
        ).limit(limit).all()

        return jsonify({
            "ok": True,
            "data": [i.to_dict() for i in insights]
        }), 200

    except Exception as e:
        return jsonify({
            "ok": False,
            "error": f"Error fetching insights: {str(e)}"
        }), 500


@learning_bp.route('/insights', methods=['POST'])
def create_insight():
    """
    Cria um novo insight

    Body JSON:
    {
        "insight_type": "pattern",
        "title": "Times com Must Win CRITICAL têm 72% de acerto em escanteios",
        "description": "Análise detalhada...",
        "confidence": 0.85,
        "impact": "high",
        "prediction_type": "corners",
        "supporting_data": {...},
        "sample_size": 50,
        "expires_in_days": 30
    }
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({"ok": False, "error": "Request body required"}), 400

        if 'title' not in data or 'description' not in data:
            return jsonify({"ok": False, "error": "title and description are required"}), 400

        insight = LearningService.create_insight(
            db=db_session,
            insight_type=data.get('insight_type', 'pattern'),
            title=data['title'],
            description=data['description'],
            confidence=data.get('confidence'),
            impact=data.get('impact'),
            prediction_type=data.get('prediction_type'),
            supporting_data=data.get('supporting_data'),
            sample_size=data.get('sample_size'),
            expires_in_days=data.get('expires_in_days')
        )

        return jsonify({
            "ok": True,
            "message": "Insight created successfully",
            "data": insight.to_dict()
        }), 201

    except Exception as e:
        db_session.rollback()
        return jsonify({
            "ok": False,
            "error": f"Error creating insight: {str(e)}"
        }), 500


# Cleanup ao final de cada request
@learning_bp.teardown_app_request
def shutdown_session(exception=None):
    """Remove a sessão do banco ao final de cada request"""
    from database import close_db
    close_db()
