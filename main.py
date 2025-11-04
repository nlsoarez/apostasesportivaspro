from flask import Flask, request, jsonify
import requests
from flask_cors import CORS
import os

app = Flask(__name__)
CORS(app)

# 🔒 Lendo variáveis de ambiente
API_KEY = os.getenv("API_KEY")
API_HOST = os.getenv("API_HOST")

if not API_KEY or not API_HOST:
    raise ValueError("As variáveis de ambiente API_KEY e API_HOST não foram configuradas corretamente!")

headers = {
    "x-rapidapi-key": API_KEY,
    "x-rapidapi-host": API_HOST
}

# ============================================================
# 🧠 Tradutor local simples EN → PT-BR
# ============================================================
def traduzir(texto):
    if not texto:
        return texto
    traducoes = {
        "stadium": "estádio",
        "arena": "arena",
        "city": "cidade",
        "team": "time",
        "home": "casa",
        "away": "fora",
        "match": "partida",
        "round": "rodada",
        "win": "vitória",
        "draw": "empate",
        "lose": "derrota"
    }
    for en, pt in traducoes.items():
        texto = texto.replace(en.capitalize(), pt.capitalize()).replace(en, pt)
    return texto

def traduzir_objeto(dado):
    if isinstance(dado, dict):
        return {k: traduzir_objeto(v) for k, v in dado.items()}
    elif isinstance(dado, list):
        return [traduzir_objeto(i) for i in dado]
    elif isinstance(dado, str):
        return traduzir(dado)
    return dado

# ============================================================
# 📅 Jogos do dia
# ============================================================
@app.route("/fixtures", methods=["GET"])
def fixtures():
    date = request.args.get("date")
    league = request.args.get("league")
    url = f"https://{API_HOST}/v3/fixtures?date={date}&league={league}"

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        return jsonify(traduzir_objeto(data))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ============================================================
# 🏆 Classificação
# ============================================================
@app.route("/standings", methods=["GET"])
def standings():
    league = request.args.get("league")
    season = request.args.get("season")
    url = f"https://{API_HOST}/v3/standings?league={league}&season={season}"

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        return jsonify(traduzir_objeto(data))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ============================================================
# 💰 Odds
# ============================================================
@app.route("/odds", methods=["GET"])
def odds():
    fixture = request.args.get("fixture")
    url = f"https://{API_HOST}/v3/odds?fixture={fixture}"

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        return jsonify(traduzir_objeto(data))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ============================================================
# 📊 Estatísticas do time
# ============================================================
@app.route("/team_stats", methods=["GET"])
def team_stats():
    team = request.args.get("team")
    league = request.args.get("league")
    season = request.args.get("season")
    url = f"https://{API_HOST}/v3/teams/statistics?team={team}&league={league}&season={season}"

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        return jsonify(traduzir_objeto(data))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ============================================================
# ⚽ Artilheiros
# ============================================================
@app.route("/topscorers", methods=["GET"])
def topscorers():
    league = request.args.get("league")
    season = request.args.get("season")
    url = f"https://{API_HOST}/v3/players/topscorers?league={league}&season={season}"

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        return jsonify(traduzir_objeto(data))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ============================================================
# 🏠 Rota inicial
# ============================================================
@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "status": "✅ API Apostas Futebol Pro ativa!",
        "mensagem": "Tradução automática ativada (EN → PT-BR)",
        "endpoints": {
            "/fixtures": "Partidas por data e liga",
            "/standings": "Classificação atual",
            "/odds": "Odds e probabilidades",
            "/team_stats": "Estatísticas do time",
            "/topscorers": "Artilheiros"
        }
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
