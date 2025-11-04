from flask import Flask, request, jsonify
import requests
from flask_cors import CORS
import os

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

@app.after_request
def after_request(response):
    response.headers.add("Access-Control-Allow-Origin", "*")
    response.headers.add("Access-Control-Allow-Headers", "Content-Type,Authorization")
    response.headers.add("Access-Control-Allow-Methods", "GET,PUT,POST,DELETE,OPTIONS")
    return response

# ==============================================================
# 🔒 Variáveis de ambiente (Render)
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
# 🔁 Função auxiliar para chamar a API-Football
# ==============================================================
def call_api_football(path: str, params: dict):
    url = f"https://{API_HOST}{path}"
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=15)

        # Log básico no Render (aparece nos logs)
        print(f"[API-FOOTBALL] {url} -> {resp.status_code}")

        # Tenta parsear JSON; se não der, retorna texto cru
        try:
            data = resp.json()
        except ValueError:
            data = {"raw": resp.text}

        if resp.ok:
            return jsonify({"ok": True, "status_code": resp.status_code, "data": data}), resp.status_code
        else:
            # Erro vindo da API externa
            return (
                jsonify({
                    "ok": False,
                    "status_code": resp.status_code,
                    "error": "Erro ao chamar API-Football",
                    "details": data
                }),
                resp.status_code
            )

    except requests.exceptions.RequestException as e:
        # Erro de rede / timeout / etc
        print(f"[API-FOOTBALL][ERROR] {e}")
        return (
            jsonify({
                "ok": False,
                "status_code": 500,
                "error": "Exceção ao chamar API-Football",
                "details": str(e)
            }),
            500
        )

# ==============================================================
# 📅 1️⃣ Jogos do dia (fixtures)
# ==============================================================
@app.route("/fixtures", methods=["GET"])
def fixtures():
    date = request.args.get("date")
    league = request.args.get("league")
    params = {"date": date, "league": league}
    return call_api_football("/v3/fixtures", params)

# ==============================================================
# 🏆 2️⃣ Classificação do campeonato
# ==============================================================
@app.route("/standings", methods=["GET"])
def standings():
    league = request.args.get("league")
    season = request.args.get("season")
    params = {"league": league, "season": season}
    return call_api_football("/v3/standings", params)

# ==============================================================
# 💰 3️⃣ Odds e probabilidades
# ==============================================================
@app.route("/odds", methods=["GET"])
def odds():
    fixture = request.args.get("fixture")
    params = {"fixture": fixture}
    return call_api_football("/v3/odds", params)

# ==============================================================
# 📊 4️⃣ Estatísticas de um time
# ==============================================================
@app.route("/team_stats", methods=["GET"])
def team_stats():
    team = request.args.get("team")
    league = request.args.get("league")
    season = request.args.get("season")
    params = {"team": team, "league": league, "season": season}
    return call_api_football("/v3/teams/statistics", params)

# ==============================================================
# ⚽ 5️⃣ Artilheiros do campeonato
# ==============================================================
@app.route("/topscorers", methods=["GET"])
def topscorers():
    league = request.args.get("league")
    season = request.args.get("season")
    params = {"league": league, "season": season}
    return call_api_football("/v3/players/topscorers", params)

# ==============================================================
# 🏠 Home
# ==============================================================
@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "status": "✅ API Apostas Futebol Pro ativa e operacional!",
        "mensagem": "Use os endpoints abaixo para acessar dados reais de futebol:",
        "endpoints": {
            "/fixtures": "Partidas por data e liga",
            "/standings": "Classificação atual do campeonato",
            "/odds": "Probabilidades e odds por jogo",
            "/team_stats": "Estatísticas de um time específico",
            "/topscorers": "Artilheiros do campeonato"
        }
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
