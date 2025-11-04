from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os
from backup_scraper import (
    get_fixtures_backup,
    get_standings_backup,
    get_topscorers_backup
)

app = Flask(__name__)
CORS(app)

# ==============================================================
# 🔐 VARIÁVEIS DE AMBIENTE (Render)
# ==============================================================
API_KEY = os.getenv("API_KEY")
API_HOST = os.getenv("API_HOST")

if not API_KEY or not API_HOST:
    raise ValueError("As variáveis de ambiente API_KEY e API_HOST não foram configuradas corretamente!")

headers = {
    "x-rapidapi-key": API_KEY,
    "x-rapidapi-host": API_HOST
}

# ==============================================================
# 🔁 Função genérica com fallback automático
# ==============================================================
def call_api_football(path, params):
    url = f"https://{API_HOST}{path}"
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=15)

        # ✅ API funcionando normalmente
        if resp.ok:
            return jsonify(resp.json())

        # ⚠️ Se a API retornar erro, ativar o backup
        print(f"⚠️ API-Football erro {resp.status_code}, ativando fallback...")
        return jsonify(fallback_handler(path))

    except Exception as e:
        print(f"🚨 Falha geral na API-Football: {e}")
        return jsonify(fallback_handler(path))


# ==============================================================
# 🧩 Função de fallback automático
# ==============================================================
def fallback_handler(path):
    if "/fixtures" in path:
        return get_fixtures_backup()
    elif "/standings" in path:
        return get_standings_backup()
    elif "/players/topscorers" in path:
        return get_topscorers_backup()
    else:
        return {"erro": "Fonte alternativa não disponível para este endpoint."}


# ==============================================================
# 📅 1️⃣ Jogos do dia
# ==============================================================
@app.route("/fixtures", methods=["GET"])
def fixtures():
    date = request.args.get("date")
    league = request.args.get("league")
    return call_api_football("/v3/fixtures", {"date": date, "league": league})


# ==============================================================
# 🏆 2️⃣ Classificação
# ==============================================================
@app.route("/standings", methods=["GET"])
def standings():
    league = request.args.get("league")
    season = request.args.get("season")
    return call_api_football("/v3/standings", {"league": league, "season": season})


# ==============================================================
# 💰 3️⃣ Odds (mantém apenas na API oficial)
# ==============================================================
@app.route("/odds", methods=["GET"])
def odds():
    fixture = request.args.get("fixture")
    return call_api_football("/v3/odds", {"fixture": fixture})


# ==============================================================
# 📊 4️⃣ Estatísticas do time
# ==============================================================
@app.route("/team_stats", methods=["GET"])
def team_stats():
    team = request.args.get("team")
    league = request.args.get("league")
    season = request.args.get("season")
    return call_api_football("/v3/teams/statistics", {"team": team, "league": league, "season": season})


# ==============================================================
# ⚽ 5️⃣ Artilheiros
# ==============================================================
@app.route("/topscorers", methods=["GET"])
def topscorers():
    league = request.args.get("league")
    season = request.args.get("season")
    return call_api_football("/v3/players/topscorers", {"league": league, "season": season})


# ==============================================================
# 🏠 6️⃣ Rota inicial
# ==============================================================
@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "status": "✅ API Apostas Futebol Pro ativa!",
        "mensagem": "Endpoints disponíveis:",
        "endpoints": {
            "/fixtures": "Jogos por data e liga",
            "/standings": "Classificação do campeonato",
            "/odds": "Odds e probabilidades",
            "/team_stats": "Estatísticas de um time",
            "/topscorers": "Artilheiros do campeonato"
        }
    })


# ==============================================================
# 🚀 Inicialização
# ==============================================================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
