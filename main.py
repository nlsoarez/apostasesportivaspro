from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import requests
import json
from datetime import datetime

app = Flask(__name__)
CORS(app)

# ============================================================
# 🔐 Config – API-Football (via RapidAPI)
# ============================================================

API_KEY = os.getenv("API_KEY")          # sua chave do RapidAPI
API_HOST = os.getenv("API_HOST") or "api-football-v1.p.rapidapi.com"

headers_api = {
    "x-rapidapi-key": API_KEY or "",
    "x-rapidapi-host": API_HOST
}

print(f"🔑 API Key configurada: {bool(API_KEY)}")
print(f"🌐 API Host: {API_HOST}")

# ============================================================
# 🔧 Função auxiliar para chamar a API
# ============================================================

def call_api_football(path, params):
    """
    Chama a API-Football e retorna os dados
    Retorna (json, erro) — se json != None, deu certo
    """
    if not API_KEY:
        return None, "API_KEY não configurada nas variáveis de ambiente."

    url = f"https://{API_HOST}{path}"
    
    try:
        print(f"📡 Chamando API: {path} com params: {params}")
        resp = requests.get(url, headers=headers_api, params=params, timeout=12)
        
        if resp.status_code == 200:
            return resp.json(), None
            
        error_msg = f"Status {resp.status_code} da API-Football"
        print(f"❌ Erro: {error_msg}")
        return None, error_msg
        
    except Exception as e:
        error_msg = f"Exceção ao chamar API-Football: {e}"
        print(f"❌ Erro: {error_msg}")
        return None, error_msg

# ============================================================
# 📅 Endpoint 1 – Fixtures (Jogos)
# ============================================================

@app.route("/fixtures", methods=["GET"])
def fixtures():
    date = request.args.get("date")      # ex: 2025-11-05
    league = request.args.get("league")  # ex: 71

    if not date or not league:
        return jsonify({
            "ok": False,
            "error": "Parâmetros 'date' e 'league' são obrigatórios."
        }), 400

    params = {"date": date, "league": league}
    data_api, error_api = call_api_football("/v3/fixtures", params)

    if data_api is not None:
        return jsonify({
            "ok": True,
            "source": "api-football",
            "data": data_api
        })

    # Se falhou, retorna erro
    return jsonify({
        "ok": False,
        "error": error_api
    }), 502

# ============================================================
# 🏆 Endpoint 2 – Standings (Classificação)
# ============================================================

@app.route("/standings", methods=["GET"])
def standings():
    league = request.args.get("league")
    season = request.args.get("season")

    if not league or not season:
        return jsonify({
            "ok": False,
            "error": "Parâmetros 'league' e 'season' são obrigatórios."
        }), 400

    params = {"league": league, "season": season}
    data_api, error_api = call_api_football("/v3/standings", params)

    if data_api is not None:
        return jsonify({
            "ok": True,
            "source": "api-football",
            "data": data_api
        })

    return jsonify({"ok": False, "error": error_api}), 502

# ============================================================
# 💰 Endpoint 3 – Odds (Probabilidades)
# ============================================================

@app.route("/odds", methods=["GET"])
def odds():
    fixture = request.args.get("fixture")
    
    if not fixture:
        return jsonify({
            "ok": False,
            "error": "Parâmetro 'fixture' é obrigatório."
        }), 400

    params = {"fixture": fixture}
    data_api, error_api = call_api_football("/v3/odds", params)

    if data_api is not None:
        return jsonify({
            "ok": True,
            "source": "api-football",
            "data": data_api
        })

    return jsonify({"ok": False, "error": error_api}), 502

# ============================================================
# 📊 Endpoint 4 – Team Stats (Estatísticas)
# ============================================================

@app.route("/team_stats", methods=["GET"])
def team_stats():
    team = request.args.get("team")
    league = request.args.get("league")
    season = request.args.get("season")

    if not team or not league or not season:
        return jsonify({
            "ok": False,
            "error": "Parâmetros 'team', 'league' e 'season' são obrigatórios."
        }), 400

    params = {"team": team, "league": league, "season": season}
    data_api, error_api = call_api_football("/v3/teams/statistics", params)

    if data_api is not None:
        return jsonify({
            "ok": True,
            "source": "api-football",
            "data": data_api
        })

    return jsonify({"ok": False, "error": error_api}), 502

# ============================================================
# ⚽ Endpoint 5 – Top Scorers (Artilheiros)
# ============================================================

@app.route("/topscorers", methods=["GET"])
def topscorers():
    league = request.args.get("league")
    season = request.args.get("season")

    if not league or not season:
        return jsonify({
            "ok": False,
            "error": "Parâmetros 'league' e 'season' são obrigatórios."
        }), 400

    params = {"league": league, "season": season}
    data_api, error_api = call_api_football("/v3/players/topscorers", params)

    if data_api is not None:
        return jsonify({
            "ok": True,
            "source": "api-football",
            "data": data_api
        })

    return jsonify({"ok": False, "error": error_api}), 502

# ============================================================
# 📈 Health Check (para monitoramento)
# ============================================================

@app.route("/health", methods=["GET"])
def health():
    """Verifica se a API está funcionando"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "api_configured": bool(API_KEY),
        "version": "1.0.0"
    })

# ============================================================
# 🏠 Rota inicial – informações da API
# ============================================================

@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "nome": "🏆 API Apostas Futebol Pro",
        "versao": "1.0.0",
        "status": "✅ Online",
        "mensagem": "Use os endpoints abaixo para buscar dados de futebol",
        "endpoints": {
            "/fixtures": "Buscar jogos - Params: date=YYYY-MM-DD, league=ID",
            "/standings": "Classificação - Params: league=ID, season=YYYY",
            "/odds": "Probabilidades - Params: fixture=ID",
            "/team_stats": "Estatísticas - Params: team=ID, league=ID, season=YYYY",
            "/topscorers": "Artilheiros - Params: league=ID, season=YYYY",
            "/health": "Status da API"
        },
        "codigos_principais": {
            "brasil": {
                "71": "Brasileirão Série A",
                "72": "Brasileirão Série B",
                "73": "Copa do Brasil"
            },
            "europa": {
                "39": "Premier League",
                "140": "La Liga",
                "135": "Serie A",
                "78": "Bundesliga",
                "61": "Ligue 1",
                "2": "Champions League"
            },
            "americas": {
                "13": "Libertadores",
                "11": "Copa Sul-Americana"
            }
        },
        "exemplos": {
            "jogos_hoje": f"/fixtures?date={datetime.now().strftime('%Y-%m-%d')}&league=71",
            "classificacao": "/standings?league=71&season=2025",
            "artilheiros": "/topscorers?league=71&season=2025"
        },
        "documentacao": "https://www.api-football.com/documentation-v3",
        "api_key_configurada": bool(API_KEY)
    })

# ============================================================
# 🎛️ Tratamento de Erros
# ============================================================

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        "ok": False,
        "error": "Endpoint não encontrado. Acesse / para ver os endpoints disponíveis."
    }), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        "ok": False,
        "error": "Erro interno do servidor."
    }), 500

# ============================================================
# ▶️ Iniciar servidor
# ============================================================

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    debug = os.getenv("FLASK_ENV") == "development"
    
    print("=" * 50)
    print("🚀 API APOSTAS FUTEBOL PRO")
    print("=" * 50)
    print(f"📍 Porta: {port}")
    print(f"🔧 Debug: {debug}")
    print(f"🔑 API Key: {'✅ Configurada' if API_KEY else '❌ NÃO CONFIGURADA'}")
    print(f"🌐 Acesse: http://localhost:{port}")
    print("=" * 50)
    
    app.run(host="0.0.0.0", port=port, debug=debug)
