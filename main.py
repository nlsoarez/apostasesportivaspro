from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import requests
from bs4 import BeautifulSoup

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


def call_api_football(path, params):
    """
    Tenta chamar a API-Football.
    Retorna (json, erro) — se json != None, deu certo; se None, veja erro.
    """
    if not API_KEY:
        return None, "API_KEY não configurada nas variáveis de ambiente."

    url = f"https://{API_HOST}{path}"
    try:
        resp = requests.get(url, headers=headers_api, params=params, timeout=12)
        if resp.status_code == 200:
            return resp.json(), None
        return None, f"Status {resp.status_code} da API-Football: {resp.text[:200]}"
    except Exception as e:
        return None, f"Exceção ao chamar API-Football: {e}"


# ============================================================
# 🔁 Backup genérico via web scraping (EXEMPLO)
# ============================================================

def backup_fixtures_from_web(date: str, league: str):
    """
    Exemplo de backup: busca jogos em um site público de resultados.
    ➜ Você PRECISA ajustar:
      - a URL
      - os seletores CSS
    """
    try:
        # TODO: troque essa URL por um site/rota real que liste jogos por data
        url = f"https://example.com/fixtures?date={date}&league={league}"

        resp = requests.get(url, timeout=12)
        if resp.status_code != 200:
            return None, f"Backup HTTP {resp.status_code} ao acessar {url}"

        html = resp.text
        soup = BeautifulSoup(html, "html.parser")

        jogos = []
        # TODO: ajuste esse seletor e os sub-seletores conforme o site escolhido
        for item in soup.select(".fixture-item"):
            home = item.select_one(".team-home").get_text(strip=True)
            away = item.select_one(".team-away").get_text(strip=True)
            hora = item.select_one(".kickoff-time").get_text(strip=True)

            jogos.append({
                "home": home,
                "away": away,
                "time": hora
            })

        if not jogos:
            return None, "Backup não encontrou jogos (ver seletores/HTML)."

        return {"fixtures": jogos}, None

    except Exception as e:
        return None, f"Erro no backup web: {e}"


# ============================================================
# 📅 Endpoint 1 – Fixtures (com backup)
# ============================================================

@app.route("/fixtures", methods=["GET"])
def fixtures():
    date = request.args.get("date")   # ex: 2025-11-05
    league = request.args.get("league")  # ex: 71

    if not date or not league:
        return jsonify({
            "ok": False,
            "error": "Parâmetros 'date' e 'league' são obrigatórios."
        }), 400

    params = {"date": date, "league": league}

    # 1️⃣ Tenta API-Football
    data_api, error_api = call_api_football("/v3/fixtures", params)

    if data_api is not None:
        return jsonify({
            "ok": True,
            "source": "api-football",
            "data": data_api
        })

    # 2️⃣ Se falhou, tenta backup web
    data_backup, error_backup = backup_fixtures_from_web(date, league)

    if data_backup is not None:
        return jsonify({
            "ok": True,
            "source": "backup-web",
            "warning": error_api,
            "data": data_backup
        })

    # 3️⃣ Se nada funcionou, devolve erro
    return jsonify({
        "ok": False,
        "error": "Nenhuma fonte conseguiu retornar dados.",
        "api_error": error_api,
        "backup_error": error_backup
    }), 502


# ============================================================
# 🏆 Classificação – só API-Football (sem backup por enquanto)
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
        return jsonify({"ok": True, "source": "api-football", "data": data_api})

    return jsonify({"ok": False, "error": error_api}), 502


# ============================================================
# 💰 Odds – só API-Football
# ============================================================

@app.route("/odds", methods=["GET"])
def odds():
    fixture = request.args.get("fixture")
    if not fixture:
        return jsonify({"ok": False, "error": "Parâmetro 'fixture' é obrigatório."}), 400

    params = {"fixture": fixture}
    data_api, error_api = call_api_football("/v3/odds", params)

    if data_api is not None:
        return jsonify({"ok": True, "source": "api-football", "data": data_api})

    return jsonify({"ok": False, "error": error_api}), 502


# ============================================================
# 📊 Estatísticas de time – só API-Football
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
        return jsonify({"ok": True, "source": "api-football", "data": data_api})

    return jsonify({"ok": False, "error": error_api}), 502


# ============================================================
# ⚽ Artilheiros – só API-Football
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
        return jsonify({"ok": True, "source": "api-football", "data": data_api})

    return jsonify({"ok": False, "error": error_api}), 502


# ============================================================
# 🌐 Página com o widget (front-end)
# ============================================================

@app.route("/app", methods=["GET"])
def app_page():
    # serve o index.html que está na raiz do projeto
    return send_from_directory(".", "index.html")


# ============================================================
# 🏠 Rota inicial – info da API
# ============================================================

@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "status": "✅ API Apostas Esportivas Pro ativa",
        "mensagem": "Use /fixtures, /standings, /odds, /team_stats, /topscorers ou abra /app para o painel com widgets.",
        "has_api_key": bool(API_KEY),
        "api_host": API_HOST,
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
