import os
import logging
from flask import Flask, jsonify, request
from flask_cors import CORS
from werkzeug.middleware.proxy_fix import ProxyFix
import requests
from dotenv import load_dotenv

# =======================
# Configurações iniciais
# =======================
load_dotenv()
app = Flask(__name__)
CORS(app)
app.wsgi_app = ProxyFix(app.wsgi_app)

# Logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

API_KEY = os.getenv("API_KEY")
API_HOST = "v3.football.api-sports.io"
API_TIMEOUT = float(os.getenv("API_TIMEOUT", "10"))
HEADERS_API = {"x-apisports-key": API_KEY}

# =======================
# Funções utilitárias
# =======================
def call_api_football(endpoint, params):
    """Chama a API-Football e retorna (data, error)."""
    if not API_KEY:
        return None, "API_KEY não configurada"

    url = f"https://{API_HOST}{endpoint}"
    try:
        response = requests.get(url, headers=HEADERS_API, params=params, timeout=API_TIMEOUT)
        if response.status_code != 200:
            logger.error(f"[API] HTTP {response.status_code} -> {endpoint}")
            return None, f"Erro HTTP {response.status_code}"

        data = response.json()
        if "errors" in data and data["errors"]:
            return None, str(data["errors"])
        return data, None

    except Exception as e:
        logger.error(f"[API Exception] {str(e)}")
        return None, str(e)

def error_response(msg, status=400):
    return jsonify({"ok": False, "error": msg}), status

# =======================
# Endpoints básicos
# =======================
@app.route("/")
def home():
    return jsonify({
        "ok": True,
        "name": "Apostas Esportivas Pro API",
        "version": "4.1",
        "description": "API profissional para integração com GPTs e análises esportivas",
        "endpoints": {
            "base": ["/health", "/fixtures", "/standings", "/teams", "/teams/statistics", "/players/topscorers"],
            "avancados": ["/fixtures/headtohead", "/injuries", "/odds", "/predictions", "/fixtures/live"],
            "profissionais": ["/analysis/corners", "/analysis/cards", "/analysis/complete", "/analysis/value"]
        }
    })

@app.route("/health")
def health():
    return jsonify({"ok": True, "message": "API operacional"})


@app.route("/fixtures", methods=["GET"])
def fixtures():
    league = request.args.get("league")
    date = request.args.get("date")
    round_param = request.args.get("round")
    season = request.args.get("season", "2025")
    status = request.args.get("status")
    timezone = request.args.get("timezone", "America/Sao_Paulo")

    if not league or (not date and not round_param):
        return error_response("Parâmetros obrigatórios ausentes: league + (date ou round)")

    params = {"league": league, "season": season, "timezone": timezone}
    if date: params["date"] = date
    if round_param: params["round"] = round_param
    if status: params["status"] = status

    data, error = call_api_football("/fixtures", params)
    if error: return error_response(error, 500)

    jogos = []
    for fixture in data.get("response", []):
        info = fixture.get("fixture", {})
        teams = fixture.get("teams", {})
        jogos.append({
            "id": info.get("id"),
            "data": info.get("date"),
            "status": info.get("status", {}).get("short"),
            "mandante": teams.get("home", {}).get("name"),
            "visitante": teams.get("away", {}).get("name"),
        })
    return jsonify({"ok": True, "total": len(jogos), "jogos": jogos})


@app.route("/standings")
def standings():
    league = request.args.get("league")
    season = request.args.get("season", "2025")
    if not league: return error_response("Parâmetro 'league' obrigatório")

    data, error = call_api_football("/standings", {"league": league, "season": season})
    if error: return error_response(error, 500)
    return jsonify({"ok": True, "standings": data.get("response", [])})


@app.route("/teams/statistics")
def team_statistics():
    team = request.args.get("team")
    league = request.args.get("league")
    season = request.args.get("season", "2025")
    if not (team and league): return error_response("Parâmetros 'team' e 'league' obrigatórios")

    data, error = call_api_football("/teams/statistics", {"team": team, "league": league, "season": season})
    if error: return error_response(error, 500)
    return jsonify({"ok": True, "stats": data.get("response", {})})


@app.route("/players/topscorers")
def top_scorers():
    league = request.args.get("league")
    season = request.args.get("season", "2025")
    if not league: return error_response("Parâmetro 'league' obrigatório")

    data, error = call_api_football("/players/topscorers", {"league": league, "season": season})
    if error: return error_response(error, 500)
    return jsonify({"ok": True, "artilheiros": data.get("response", [])})


# =======================
# Endpoints avançados
# =======================
@app.route("/fixtures/headtohead")
def head_to_head():
    h2h = request.args.get("h2h")
    if not h2h: return error_response("Parâmetro 'h2h' obrigatório")

    data, error = call_api_football("/fixtures/headtohead", {"h2h": h2h})
    if error: return error_response(error, 500)

    resultados = []
    for match in data.get("response", [])[:10]:
        placar = match.get("goals", {})
        resultados.append({
            "mandante": match["teams"]["home"]["name"],
            "visitante": match["teams"]["away"]["name"],
            "placar": f"{placar.get('home', 0)}x{placar.get('away', 0)}"
        })
    return jsonify({"ok": True, "total": len(resultados), "resultados": resultados})


@app.route("/injuries")
def injuries():
    league = request.args.get("league")
    team = request.args.get("team")
    season = request.args.get("season", "2025")
    if not (league and team): return error_response("Parâmetros 'league' e 'team' obrigatórios")

    data, error = call_api_football("/injuries", {"league": league, "team": team, "season": season})
    if error: return error_response(error, 500)

    lesoes = []
    for injury in data.get("response", []):
        player = injury.get("player", {})
        detail = injury.get("injury", {})
        lesoes.append({
            "jogador": player.get("name"),
            "tipo": detail.get("type"),
            "motivo": detail.get("reason")
        })
    return jsonify({"ok": True, "total": len(lesoes), "lesoes": lesoes})


@app.route("/odds")
def odds():
    fixture = request.args.get("fixture")
    if not fixture: return error_response("Parâmetro 'fixture' obrigatório")

    data, error = call_api_football("/odds", {"fixture": fixture})
    if error: return error_response(error, 500)
    return jsonify({"ok": True, "odds": data.get("response", [])})


@app.route("/predictions")
def predictions():
    fixture = request.args.get("fixture")
    if not fixture: return error_response("Parâmetro 'fixture' obrigatório")

    data, error = call_api_football("/predictions", {"fixture": fixture})
    if error: return error_response(error, 500)
    return jsonify({"ok": True, "predicoes": data.get("response", [])})


@app.route("/fixtures/live")
def live_fixtures():
    data, error = call_api_football("/fixtures", {"live": "all"})
    if error: return error_response(error, 500)

    partidas = []
    for fixture in data.get("response", [])[:20]:
        info = fixture.get("fixture", {})
        teams = fixture.get("teams", {})
        partidas.append({
            "id": info.get("id"),
            "status": info.get("status", {}).get("short"),
            "minuto": info.get("status", {}).get("elapsed"),
            "mandante": teams.get("home", {}).get("name"),
            "visitante": teams.get("away", {}).get("name"),
        })
    return jsonify({"ok": True, "partidas": partidas})


# =======================
# Endpoints profissionais
# =======================
@app.route("/analysis/corners")
def analysis_corners():
    team_home = request.args.get("team_home")
    team_away = request.args.get("team_away")
    league = request.args.get("league")
    season = request.args.get("season", "2025")
    if not (team_home and team_away and league): 
        return error_response("Parâmetros obrigatórios ausentes")

    stats_home, _ = call_api_football("/teams/statistics", {"team": team_home, "league": league, "season": season})
    stats_away, _ = call_api_football("/teams/statistics", {"team": team_away, "league": league, "season": season})

    try:
        media_home = stats_home["response"]["fixtures"]["corners"]["for"]["average"]["home"]
        media_away = stats_away["response"]["fixtures"]["corners"]["for"]["average"]["away"]
        estimativa = round(float(media_home) + float(media_away), 1)
    except Exception:
        estimativa = 10.0

    analise = {
        "time_casa": {"id": team_home},
        "time_fora": {"id": team_away},
        "estimativa_total": estimativa,
        "sugestoes": [{
            "mercado": "Over 9.5 Escanteios Totais",
            "confianca": 5 if estimativa >= 10 else 4,
            "value_estimado": "+20%" if estimativa >= 10 else "+10%"
        }]
    }
    return jsonify({"ok": True, "analise_escanteios": analise})


@app.route("/analysis/cards")
def analysis_cards():
    team_home = request.args.get("team_home")
    team_away = request.args.get("team_away")
    league = request.args.get("league")
    season = request.args.get("season", "2025")
    if not (team_home and team_away and league): 
        return error_response("Parâmetros obrigatórios ausentes")

    stats_home, _ = call_api_football("/teams/statistics", {"team": team_home, "league": league, "season": season})
    stats_away, _ = call_api_football("/teams/statistics", {"team": team_away, "league": league, "season": season})

    try:
        media_home = stats_home["response"]["cards"]["yellow"]["average"]["home"]
        media_away = stats_away["response"]["cards"]["yellow"]["average"]["away"]
        estimativa = round(float(media_home) + float(media_away), 1)
    except Exception:
        estimativa = 5.5

    analise = {
        "estimativa_total": estimativa,
        "sugestoes": [{
            "mercado": "Over 5.5 Cartões Totais",
            "confianca": 5 if estimativa >= 5.5 else 4,
            "value_estimado": "+25%" if estimativa >= 5.5 else "+10%"
        }]
    }
    return jsonify({"ok": True, "analise_cartoes": analise})


@app.route("/analysis/value")
def analysis_value():
    try:
        odd = float(request.args.get("odd"))
        prob = float(request.args.get("probability"))
    except:
        return error_response("Parâmetros inválidos: odd e probability")

    value = round((prob * odd) - 1, 3)
    return jsonify({"ok": True, "value": value})


# =======================
# Handlers de erro
# =======================
@app.errorhandler(404)
def not_found(e):
    return jsonify({"ok": False, "error": "Rota não encontrada"}), 404

@app.errorhandler(500)
def internal_error(e):
    return jsonify({"ok": False, "error": "Erro interno no servidor"}), 500


if __name__ == "__main__":
    app.run(debug=True)
