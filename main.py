from flask import Flask, request, jsonify
import requests
from flask_cors import CORS
import os

# ==============================================================
# 🌐 Configuração inicial
# ==============================================================
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
# 📅 1️⃣ Endpoint: Jogos do dia
# ==============================================================
@app.route("/fixtures", methods=["GET"])
def fixtures():
    date = request.args.get("date")
    league = request.args.get("league")
    url = f"https://{API_HOST}/v3/fixtures?date={date}&league={league}"

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return jsonify(response.json())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ==============================================================
# 🏆 2️⃣ Endpoint: Classificação do campeonato
# ==============================================================
@app.route("/standings", methods=["GET"])
def standings():
    league = request.args.get("league")
    season = request.args.get("season")
    url = f"https://{API_HOST}/v3/standings?league={league}&season={season}"

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return jsonify(response.json())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ==============================================================
# 💰 3️⃣ Endpoint: Odds e probabilidades
# ==============================================================
@app.route("/odds", methods=["GET"])
def odds():
    fixture = request.args.get("fixture")
    url = f"https://{API_HOST}/v3/odds?fixture={fixture}"

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return jsonify(response.json())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ==============================================================
# 📊 4️⃣ Endpoint: Estatísticas de um time
# ==============================================================
@app.route("/team_stats", methods=["GET"])
def team_stats():
    team = request.args.get("team")
    league = request.args.get("league")
    season = request.args.get("season")
    url = f"https://{API_HOST}/v3/teams/statistics?team={team}&league={league}&season={season}"

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return jsonify(response.json())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ==============================================================
# ⚽ 5️⃣ Endpoint: Artilheiros do campeonato
# ==============================================================
@app.route("/topscorers", methods=["GET"])
def topscorers():
    league = request.args.get("league")
    season = request.args.get("season")
    url = f"https://{API_HOST}/v3/players/topscorers?league={league}&season={season}"

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return jsonify(response.json())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ==============================================================
# 🏠 Endpoint inicial (status)
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

# ==============================================================
# 🚀 Execução principal
# ==============================================================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
