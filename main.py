from flask import Flask, request, jsonify
import requests
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

API_KEY = "5a11026630mshadb57d19aee8e4ap11819ajsn118cac576d4f"
API_HOST = "api-football-v1.p.rapidapi.com"

headers = {
    "x-rapidapi-key": API_KEY,
    "x-rapidapi-host": API_HOST
}

# 🔹 Endpoint 1: Jogos do dia
@app.route("/fixtures", methods=["GET"])
def fixtures():
    date = request.args.get("date")
    league = request.args.get("league")
    url = f"https://{API_HOST}/v3/fixtures?date={date}&league={league}"
    r = requests.get(url, headers=headers)
    return jsonify(r.json())

# 🔹 Endpoint 2: Classificação
@app.route("/standings", methods=["GET"])
def standings():
    league = request.args.get("league")
    season = request.args.get("season")
    url = f"https://{API_HOST}/v3/standings?league={league}&season={season}"
    r = requests.get(url, headers=headers)
    return jsonify(r.json())

# 🔹 Endpoint 3: Odds e probabilidades
@app.route("/odds", methods=["GET"])
def odds():
    fixture = request.args.get("fixture")
    url = f"https://{API_HOST}/v3/odds?fixture={fixture}"
    r = requests.get(url, headers=headers)
    return jsonify(r.json())

# 🔹 Endpoint 4: Estatísticas do time
@app.route("/team_stats", methods=["GET"])
def team_stats():
    team = request.args.get("team")
    league = request.args.get("league")
    season = request.args.get("season")
    url = f"https://{API_HOST}/v3/teams/statistics?team={team}&league={league}&season={season}"
    r = requests.get(url, headers=headers)
    return jsonify(r.json())

# 🔹 Endpoint 5: Artilheiros
@app.route("/topscorers", methods=["GET"])
def topscorers():
    league = request.args.get("league")
    season = request.args.get("season")
    url = f"https://{API_HOST}/v3/players/topscorers?league={league}&season={season}"
    r = requests.get(url, headers=headers)
    return jsonify(r.json())

@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "status": "API Apostas Futebol Pro ativa ✅",
        "endpoints": ["/fixtures", "/standings", "/odds", "/team_stats", "/topscorers"]
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
