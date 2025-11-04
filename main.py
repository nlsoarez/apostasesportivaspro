from flask import Flask, request, jsonify
import requests
from flask_cors import CORS
import os
from googletrans import Translator

app = Flask(__name__)
CORS(app)

# 🧠 Inicializa o tradutor
translator = Translator()

# 🔄 Função auxiliar para traduzir nomes
def traduzir_nome(nome):
    if not nome:
        return nome
    # Mapeamento manual de nomes comuns
    traducoes = {
        "Flamengo RJ": "Flamengo",
        "Palmeiras": "Palmeiras",
        "Sao Paulo": "São Paulo",
        "Atletico-MG": "Atlético-MG",
        "Corinthians": "Corinthians",
        "Botafogo RJ": "Botafogo",
        "Internacional": "Internacional",
        "Gremio": "Grêmio",
        "Vasco da Gama": "Vasco da Gama",
        "Fluminense": "Fluminense",
        "Maracana Stadium": "Estádio do Maracanã",
        "Allianz Parque": "Allianz Parque",
        "Mineirao": "Estádio Mineirão",
        "Arena Corinthians": "Neo Química Arena",
        "Beira-Rio": "Beira-Rio",
    }

    if nome in traducoes:
        return traducoes[nome]

    # Caso não esteja no dicionário, traduz automaticamente
    try:
        traducao = translator.translate(nome, src="en", dest="pt").text
        return traducao
    except Exception:
        return nome  # fallback seguro

# 🔒 Lendo as variáveis de ambiente do Render
API_KEY = os.getenv("API_KEY")
API_HOST = os.getenv("API_HOST")

if not API_KEY or not API_HOST:
    raise ValueError("As variáveis de ambiente API_KEY e API_HOST não foram configuradas corretamente!")

headers = {
    "x-rapidapi-key": API_KEY,
    "x-rapidapi-host": API_HOST
}

# ==============================================================
# 📅 Endpoint 1: Jogos do dia (Fixtures)
# ==============================================================
@app.route("/fixtures", methods=["GET"])
def fixtures():
    date = request.args.get("date")
    league = request.args.get("league")
    url = f"https://{API_HOST}/v3/fixtures?date={date}&league={league}"

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()

        # 🔄 Traduz nomes dos times e estádios
        for jogo in data.get("response", []):
            home = jogo.get("teams", {}).get("home", {})
            away = jogo.get("teams", {}).get("away", {})
            venue = jogo.get("fixture", {}).get("venue", {})

            if "name" in home:
                home["name"] = traduzir_nome(home["name"])
            if "name" in away:
                away["name"] = traduzir_nome(away["name"])
            if "name" in venue:
                venue["name"] = traduzir_nome(venue["name"])

        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ==============================================================
# 🏆 Endpoint 2: Classificação do campeonato
# ==============================================================
@app.route("/standings", methods=["GET"])
def standings():
    league = request.args.get("league")
    season = request.args.get("season")
    url = f"https://{API_HOST}/v3/standings?league={league}&season={season}"

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()

        # 🔄 Traduz nomes dos times na tabela
        for liga in data.get("response", []):
            for grupo in liga.get("league", {}).get("standings", []):
                for time in grupo:
                    if "team" in time and "name" in time["team"]:
                        time["team"]["name"] = traduzir_nome(time["team"]["name"])

        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ==============================================================
# 💰 Endpoint 3: Odds e probabilidades
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
# 📊 Endpoint 4: Estatísticas de um time
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
        data = response.json()

        # 🔄 Traduz nome do time e estádio
        if "response" in data:
            team_data = data["response"].get("team", {})
            venue = data["response"].get("venue", {})

            if "name" in team_data:
                team_data["name"] = traduzir_nome(team_data["name"])
            if "name" in venue:
                venue["name"] = traduzir_nome(venue["name"])

        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ==============================================================
# ⚽ Endpoint 5: Artilheiros do campeonato
# ==============================================================
@app.route("/topscorers", methods=["GET"])
def topscorers():
    league = request.args.get("league")
    season = request.args.get("season")
    url = f"https://{API_HOST}/v3/players/topscorers?league={league}&season={season}"

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()

        # 🔄 Traduz nomes dos times dos artilheiros
        for jogador in data.get("response", []):
            team = jogador.get("statistics", [{}])[0].get("team", {})
            if "name" in team:
                team["name"] = traduzir_nome(team["name"])

        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ==============================================================
# 🏠 Rota inicial
# ==============================================================
@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "status": "✅ API Apostas Futebol Pro ativa e operacional!",
        "mensagem": "Use os endpoints abaixo para acessar dados reais de futebol (com tradução automática PT-BR):",
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
