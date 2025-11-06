from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import requests
from datetime import datetime

app = Flask(__name__)
CORS(app)

# Configuração da API-Sports
API_KEY = os.getenv("API_KEY")
API_HOST = os.getenv("API_HOST", "v3.football.api-sports.io")

headers_api = {
    "x-apisports-key": API_KEY
}

print(f"🔑 API Key: {'✅' if API_KEY else '❌ NÃO CONFIGURADA'}")

def call_api_football(endpoint, params):
    """Chama a API-Football e retorna os dados"""
    if not API_KEY:
        return None, "API_KEY não configurada"
    
    url = f"https://{API_HOST}{endpoint}"
    
    try:
        print(f"📡 Chamando: {endpoint}")
        response = requests.get(url, headers=headers_api, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("errors") and len(data["errors"]) > 0:
                return None, str(data["errors"])
            return data, None
        else:
            return None, f"Erro {response.status_code}"
    except Exception as e:
        return None, str(e)

@app.route("/health", methods=["GET"])
def health():
    """Health check"""
    test_result = "unknown"
    try:
        response = requests.get(
            f"https://{API_HOST}/status",
            headers=headers_api if API_KEY else {},
            timeout=5
        )
        test_result = "connected" if response.status_code == 200 else "error"
    except:
        test_result = "timeout"
    
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "api_key_configured": bool(API_KEY),
        "api_host": API_HOST,
        "api_connection": test_result,
        "version": "2.1.0"
    })

@app.route("/fixtures", methods=["GET"])
def fixtures():
    """Busca jogos por data e liga"""
    date = request.args.get("date")
    league = request.args.get("league")
    season = request.args.get("season", "2024")
    
    if not date or not league:
        return jsonify({
            "ok": False,
            "error": "Parâmetros obrigatórios: date e league"
        }), 400
    
    data, error = call_api_football("/fixtures", {
        "date": date,
        "league": league,
        "season": season
    })
    
    if data:
        fixtures = data.get("response", [])
        jogos = []
        for fixture in fixtures:
            jogos.append({
                "id": fixture["fixture"]["id"],
                "data": fixture["fixture"]["date"],
                "status": fixture["fixture"]["status"]["long"],
                "time_casa": {
                    "id": fixture["teams"]["home"]["id"],
                    "nome": fixture["teams"]["home"]["name"],
                    "logo": fixture["teams"]["home"]["logo"]
                },
                "time_fora": {
                    "id": fixture["teams"]["away"]["id"],
                    "nome": fixture["teams"]["away"]["name"],
                    "logo": fixture["teams"]["away"]["logo"]
                },
                "gols": fixture["goals"]
            })
        
        return jsonify({
            "ok": True,
            "total": len(jogos),
            "jogos": jogos
        })
    
    return jsonify({"ok": False, "error": error}), 500

@app.route("/standings", methods=["GET"])
def standings():
    """Busca classificação do campeonato"""
    league = request.args.get("league")
    season = request.args.get("season", "2024")
    
    if not league:
        return jsonify({"ok": False, "error": "league obrigatório"}), 400
    
    data, error = call_api_football("/standings", {
        "league": league,
        "season": season
    })
    
    if data:
        response = data.get("response", [])
        if response:
            standings = response[0].get("league", {}).get("standings", [[]])[0]
            tabela = []
            for team in standings:
                tabela.append({
                    "posicao": team["rank"],
                    "time": team["team"]["name"],
                    "pontos": team["points"],
                    "jogos": team["all"]["played"],
                    "vitorias": team["all"]["win"],
                    "empates": team["all"]["draw"],
                    "derrotas": team["all"]["lose"],
                    "gols_pro": team["all"]["goals"]["for"],
                    "gols_contra": team["all"]["goals"]["against"],
                    "saldo": team["goalsDiff"]
                })
            
            return jsonify({
                "ok": True,
                "tabela": tabela,
                "liga": response[0]["league"]["name"]
            })
    
    return jsonify({"ok": False, "error": error}), 500

@app.route("/teams", methods=["GET"])
def teams():
    """Busca times de uma liga"""
    league = request.args.get("league")
    season = request.args.get("season", "2024")
    
    if not league:
        return jsonify({"ok": False, "error": "league obrigatório"}), 400
    
    data, error = call_api_football("/teams", {
        "league": league,
        "season": season
    })
    
    if data:
        teams_list = data.get("response", [])
        times = []
        for item in teams_list:
            team = item.get("team", {})
            times.append({
                "id": team.get("id"),
                "nome": team.get("name"),
                "logo": team.get("logo"),
                "estadio": item.get("venue", {}).get("name")
            })
        
        return jsonify({"ok": True, "total": len(times), "times": times})
    
    return jsonify({"ok": False, "error": error}), 500

@app.route("/teams/statistics", methods=["GET"])
def team_stats():
    """Busca estatísticas de um time"""
    team = request.args.get("team")
    league = request.args.get("league")
    season = request.args.get("season", "2024")
    
    if not team or not league:
        return jsonify({"ok": False, "error": "team e league obrigatórios"}), 400
    
    data, error = call_api_football("/teams/statistics", {
        "team": team,
        "league": league,
        "season": season
    })
    
    if data:
        response = data.get("response", {})
        if response:
            stats = {
                "time": response.get("team", {}).get("name"),
                "forma": response.get("form"),
                "jogos": response.get("fixtures", {}),
                "gols": response.get("goals", {})
            }
            return jsonify({"ok": True, "estatisticas": stats})
    
    return jsonify({"ok": False, "error": error}), 500

@app.route("/players/topscorers", methods=["GET"])
def topscorers():
    """Busca artilheiros do campeonato"""
    league = request.args.get("league")
    season = request.args.get("season", "2024")
    
    if not league:
        return jsonify({"ok": False, "error": "league obrigatório"}), 400
    
    data, error = call_api_football("/players/topscorers", {
        "league": league,
        "season": season
    })
    
    if data:
        scorers = data.get("response", [])[:20]
        artilheiros = []
        for item in scorers:
            player = item.get("player", {})
            stats = item.get("statistics", [{}])[0]
            artilheiros.append({
                "posicao": len(artilheiros) + 1,
                "jogador": player.get("name"),
                "time": stats.get("team", {}).get("name"),
                "gols": stats.get("goals", {}).get("total", 0)
            })
        
        return jsonify({"ok": True, "artilheiros": artilheiros})
    
    return jsonify({"ok": False, "error": error}), 500

@app.route("/", methods=["GET"])
def home():
    """Documentação"""
    return jsonify({
        "status": "✅ Online",
        "version": "2.1.0",
        "endpoints": {
            "health": "/health",
            "fixtures": "/fixtures?date=2025-11-06&league=71",
            "standings": "/standings?league=71&season=2024",
            "teams": "/teams?league=71&season=2024",
            "statistics": "/teams/statistics?team=121&league=71",
            "topscorers": "/players/topscorers?league=71&season=2024"
        }
    })

@app.errorhandler(404)
def not_found(error):
    return jsonify({"ok": False, "error": "Endpoint não encontrado"}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({"ok": False, "error": "Erro interno"}), 500

# Configuração para Vercel
from werkzeug.middleware.proxy_fix import ProxyFix
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
