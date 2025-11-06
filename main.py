"""
MAIN.PY MELHORADO - Versão 3.0
Novos endpoints adicionados:
- Head to Head (H2H)
- Injuries (Lesões)
- Odds ao vivo
- Predictions (Previsões da API)
- Transfers (Transferências)
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import requests
from datetime import datetime
from werkzeug.middleware.proxy_fix import ProxyFix

app = Flask(__name__)
CORS(app)

# Configuração
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

# ============================================================
# ENDPOINTS EXISTENTES (mantidos)
# ============================================================

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
        "version": "3.0.0"
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
        
        return jsonify({"ok": True, "total": len(jogos), "jogos": jogos})
    
    return jsonify({"ok": False, "error": error}), 500

@app.route("/standings", methods=["GET"])
def standings():
    """Busca classificação"""
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
                    "saldo": team["goalsDiff"],
                    "forma": team.get("form", "")
                })
            
            return jsonify({
                "ok": True,
                "tabela": tabela,
                "liga": response[0]["league"]["name"]
            })
    
    return jsonify({"ok": False, "error": error}), 500

@app.route("/teams", methods=["GET"])
def teams():
    """Busca times"""
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
    """Busca estatísticas"""
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
    """Busca artilheiros"""
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

# ============================================================
# 🆕 NOVOS ENDPOINTS
# ============================================================

@app.route("/fixtures/headtohead", methods=["GET"])
def headtohead():
    """
    🆕 Confronto direto entre dois times
    Exemplo: /fixtures/headtohead?h2h=127-121
    """
    h2h = request.args.get("h2h")  # Format: team1_id-team2_id
    
    if not h2h:
        return jsonify({
            "ok": False,
            "error": "Parâmetro h2h obrigatório (ex: 127-121)"
        }), 400
    
    data, error = call_api_football("/fixtures/headtohead", {"h2h": h2h})
    
    if data:
        matches = data.get("response", [])
        historico = []
        
        for match in matches[:10]:  # Últimos 10 jogos
            historico.append({
                "data": match["fixture"]["date"],
                "time_casa": match["teams"]["home"]["name"],
                "time_fora": match["teams"]["away"]["name"],
                "placar_casa": match["goals"]["home"],
                "placar_fora": match["goals"]["away"],
                "vencedor": match["teams"]["home"]["winner"] if match["teams"]["home"]["winner"] else (
                    "empate" if match["goals"]["home"] == match["goals"]["away"] else match["teams"]["away"]["name"]
                )
            })
        
        return jsonify({
            "ok": True,
            "total": len(historico),
            "historico": historico
        })
    
    return jsonify({"ok": False, "error": error}), 500

@app.route("/injuries", methods=["GET"])
def injuries():
    """
    🆕 Lesões e suspensões de um time
    Exemplo: /injuries?league=71&season=2024&team=127
    """
    league = request.args.get("league")
    season = request.args.get("season", "2024")
    team = request.args.get("team")
    
    if not league or not team:
        return jsonify({
            "ok": False,
            "error": "league e team obrigatórios"
        }), 400
    
    data, error = call_api_football("/injuries", {
        "league": league,
        "season": season,
        "team": team
    })
    
    if data:
        injuries_list = data.get("response", [])
        lesoes = []
        
        for injury in injuries_list:
            lesoes.append({
                "jogador": injury["player"]["name"],
                "tipo": injury["player"]["type"],
                "motivo": injury["player"]["reason"],
                "data": injury["fixture"]["date"]
            })
        
        return jsonify({
            "ok": True,
            "total": len(lesoes),
            "lesoes": lesoes
        })
    
    return jsonify({"ok": False, "error": error}), 500

@app.route("/odds", methods=["GET"])
def odds():
    """
    🆕 Odds de um jogo específico
    Exemplo: /odds?fixture=12345
    """
    fixture = request.args.get("fixture")
    
    if not fixture:
        return jsonify({
            "ok": False,
            "error": "fixture id obrigatório"
        }), 400
    
    data, error = call_api_football("/odds", {
        "fixture": fixture
    })
    
    if data:
        odds_data = data.get("response", [])
        
        if odds_data:
            bookmakers = odds_data[0].get("bookmakers", [])
            odds_1x2 = None
            
            # Pegar odds do primeiro bookmaker
            for bookmaker in bookmakers:
                for bet in bookmaker.get("bets", []):
                    if bet.get("name") == "Match Winner":
                        odds_1x2 = {
                            "casa": None,
                            "empate": None,
                            "fora": None
                        }
                        for value in bet.get("values", []):
                            if value["value"] == "Home":
                                odds_1x2["casa"] = float(value["odd"])
                            elif value["value"] == "Draw":
                                odds_1x2["empate"] = float(value["odd"])
                            elif value["value"] == "Away":
                                odds_1x2["fora"] = float(value["odd"])
                        break
                if odds_1x2:
                    break
            
            return jsonify({
                "ok": True,
                "odds": odds_1x2,
                "bookmaker": bookmakers[0]["name"] if bookmakers else None
            })
    
    return jsonify({"ok": False, "error": error or "Odds não disponíveis"}), 500

@app.route("/predictions", methods=["GET"])
def predictions():
    """
    🆕 Previsões da API-Sports (usa IA deles)
    Exemplo: /predictions?fixture=12345
    """
    fixture = request.args.get("fixture")
    
    if not fixture:
        return jsonify({
            "ok": False,
            "error": "fixture id obrigatório"
        }), 400
    
    data, error = call_api_football("/predictions", {
        "fixture": fixture
    })
    
    if data:
        response = data.get("response", [])
        
        if response:
            pred = response[0]
            predictions_data = pred.get("predictions", {})
            
            return jsonify({
                "ok": True,
                "previsao": {
                    "vencedor": predictions_data.get("winner", {}),
                    "placar": predictions_data.get("goals", {}),
                    "percentual_vitoria": predictions_data.get("percent", {}),
                    "conselhos": predictions_data.get("advice", "")
                },
                "comparacao": pred.get("comparison", {})
            })
    
    return jsonify({"ok": False, "error": error}), 500

@app.route("/fixtures/live", methods=["GET"])
def live_fixtures():
    """
    🆕 Jogos ao vivo agora
    Exemplo: /fixtures/live
    """
    data, error = call_api_football("/fixtures", {"live": "all"})
    
    if data:
        live_matches = data.get("response", [])
        jogos_ao_vivo = []
        
        for match in live_matches[:20]:  # Limitar a 20
            jogos_ao_vivo.append({
                "id": match["fixture"]["id"],
                "liga": match["league"]["name"],
                "time_casa": match["teams"]["home"]["name"],
                "time_fora": match["teams"]["away"]["name"],
                "placar_casa": match["goals"]["home"],
                "placar_fora": match["goals"]["away"],
                "tempo": match["fixture"]["status"]["elapsed"],
                "status": match["fixture"]["status"]["long"]
            })
        
        return jsonify({
            "ok": True,
            "total": len(jogos_ao_vivo),
            "jogos_ao_vivo": jogos_ao_vivo
        })
    
    return jsonify({"ok": False, "error": error}), 500

# ============================================================
# HOME
# ============================================================

@app.route("/", methods=["GET"])
def home():
    hoje = datetime.now().strftime('%Y-%m-%d')
    
    return jsonify({
        "status": "✅ Online",
        "version": "3.0.0",
        "novos_endpoints": {
            "headtohead": {
                "url": "/fixtures/headtohead",
                "params": "h2h (ex: 127-121)",
                "exemplo": "/fixtures/headtohead?h2h=127-121"
            },
            "injuries": {
                "url": "/injuries",
                "params": "league, team, season",
                "exemplo": "/injuries?league=71&team=127&season=2024"
            },
            "odds": {
                "url": "/odds",
                "params": "fixture (id do jogo)",
                "exemplo": "/odds?fixture=12345"
            },
            "predictions": {
                "url": "/predictions",
                "params": "fixture (id do jogo)",
                "exemplo": "/predictions?fixture=12345"
            },
            "live": {
                "url": "/fixtures/live",
                "params": "nenhum",
                "exemplo": "/fixtures/live"
            }
        },
        "endpoints_existentes": {
            "jogos": f"/fixtures?date={hoje}&league=71&season=2024",
            "classificacao": "/standings?league=71&season=2024",
            "times": "/teams?league=71&season=2024",
            "estatisticas": "/teams/statistics?team=121&league=71&season=2024",
            "artilheiros": "/players/topscorers?league=71&season=2024",
            "health": "/health"
        }
    })

@app.errorhandler(404)
def not_found(error):
    return jsonify({"ok": False, "error": "Endpoint não encontrado"}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({"ok": False, "error": "Erro interno"}), 500

# Configuração para Vercel
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
