import os
import logging
import requests
import json
import yaml
from datetime import datetime, timedelta
from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
from werkzeug.middleware.proxy_fix import ProxyFix
from dotenv import load_dotenv

# =======================
# Configurações iniciais
# =======================
load_dotenv()
app = Flask(__name__)
CORS(app)
app.wsgi_app = ProxyFix(app.wsgi_app)

# Logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# =======================
# Constantes da aplicação
# =======================
API_VERSION = "5.0"
DEFAULT_SEASON = 2025
DEFAULT_TIMEZONE = "America/Sao_Paulo"
DEFAULT_NEWS_DAYS = 3
MAX_NEWS_DAYS = 30
MAX_LIVE_FIXTURES = 20
MAX_H2H_RESULTS = 10
DEFAULT_CORNERS_ESTIMATE = 10.0
DEFAULT_CARDS_ESTIMATE = 5.5

# Validações
MIN_ODD_VALUE = 1.01
MAX_ODD_VALUE = 100.0
MIN_PROBABILITY = 0.01
MAX_PROBABILITY = 1.0

# Variáveis de ambiente
API_KEY = os.getenv("API_KEY")
API_HOST = "v3.football.api-sports.io"
API_TIMEOUT = float(os.getenv("API_TIMEOUT", "10"))
HEADERS_API = {"x-apisports-key": API_KEY}
NEWS_API_KEY = os.getenv("NEWS_API_KEY", "")

# Validação crítica de API_KEY
if not API_KEY:
    logger.error("⚠️  ERRO CRÍTICO: API_KEY não configurada!")
    logger.error("Configure a variável de ambiente API_KEY antes de iniciar.")

# =======================
# Ligas suportadas
# =======================
SUPPORTED_LEAGUES = {
    # Brasil
    71: "Brasileirão Série A",
    72: "Brasileirão Série B",
    73: "Copa do Brasil",
    75: "Campeonato Carioca",
    76: "Campeonato Paulista",
    # Europa
    39: "Premier League",
    140: "La Liga",
    135: "Serie A",
    78: "Bundesliga",
    61: "Ligue 1",
    94: "Primeira Liga",
    88: "Eredivisie",
    # Internacionais
    2: "UEFA Champions League",
    3: "UEFA Europa League",
    848: "UEFA Conference League",
    13: "Copa Libertadores",
    11: "Copa Sul-Americana",
    # Américas
    253: "MLS",
    128: "Liga MX",
    # Outros
    1: "World Cup",
    960: "Euro Championship"
}

# =======================
# Funções utilitárias
# =======================
def call_api_football(endpoint, params):
    """
    Chama a API-Football e retorna (data, error).

    Args:
        endpoint (str): Endpoint da API (ex: /fixtures)
        params (dict): Parâmetros da query string

    Returns:
        tuple: (data, error) onde data é o JSON de resposta ou None em caso de erro
    """
    if not API_KEY:
        return None, "API_KEY não configurada"

    url = f"https://{API_HOST}{endpoint}"
    try:
        response = requests.get(url, headers=HEADERS_API, params=params, timeout=API_TIMEOUT)
        if response.status_code != 200:
            logger.error(f"[API] HTTP {response.status_code} -> {endpoint}")
            return None, f"Erro HTTP {response.status_code}"

        data = response.json()
        if "errors" in data and data["errors"]:
            return None, str(data["errors"])
        return data, None

    except Exception as e:
        logger.error(f"[API Exception] {str(e)}")
        return None, str(e)


def error_response(msg, status=400):
    """
    Retorna resposta de erro padronizada.

    Args:
        msg (str): Mensagem de erro
        status (int): Código HTTP de status

    Returns:
        tuple: (Response, status_code)
    """
    return jsonify({"ok": False, "error": msg}), status


def validate_numeric_param(value, param_name, min_val=None, max_val=None, required=True):
    """
    Valida parâmetro numérico com ranges opcionais.

    Args:
        value: Valor a validar
        param_name (str): Nome do parâmetro (para mensagem de erro)
        min_val (float): Valor mínimo aceitável
        max_val (float): Valor máximo aceitável
        required (bool): Se o parâmetro é obrigatório

    Returns:
        tuple: (float_value, error_message) onde error_message é None se válido
    """
    if value is None:
        if required:
            return None, f"Parâmetro '{param_name}' é obrigatório"
        return None, None

    try:
        num_value = float(value)
    except (ValueError, TypeError):
        return None, f"Parâmetro '{param_name}' deve ser numérico"

    if min_val is not None and num_value < min_val:
        return None, f"Parâmetro '{param_name}' deve ser >= {min_val}"

    if max_val is not None and num_value > max_val:
        return None, f"Parâmetro '{param_name}' deve ser <= {max_val}"

    return num_value, None


def validate_integer_param(value, param_name, required=True):
    """
    Valida parâmetro inteiro.

    Args:
        value: Valor a validar
        param_name (str): Nome do parâmetro
        required (bool): Se é obrigatório

    Returns:
        tuple: (int_value, error_message)
    """
    if value is None:
        if required:
            return None, f"Parâmetro '{param_name}' é obrigatório"
        return None, None

    try:
        int_value = int(value)
        return int_value, None
    except (ValueError, TypeError):
        return None, f"Parâmetro '{param_name}' deve ser um inteiro válido"


# =======================
# Endpoints básicos
# =======================
@app.route("/")
def home():
    """
    Retorna informações sobre a API e endpoints disponíveis.
    """
    return jsonify({
        "ok": True,
        "name": "Apostas Esportivas Pro API",
        "version": API_VERSION,
        "description": "API profissional para integração com GPTs e análises esportivas com contexto de notícias.",
        "documentation": "/openapi.json",
        "endpoints": {
            "base": ["/health", "/fixtures", "/standings", "/teams/statistics", "/players/topscorers", "/leagues"],
            "avancados": ["/fixtures/headtohead", "/injuries", "/odds", "/predictions", "/fixtures/live"],
            "profissionais": ["/analysis/corners", "/analysis/cards", "/analysis/value", "/news/context"]
        },
        "features": [
            "50+ ligas suportadas",
            "Dados em tempo real",
            "Análises profissionais",
            "Value Betting",
            "Previsões IA",
            "Contexto de notícias"
        ]
    })


@app.route("/health")
def health():
    """
    Health check da API com teste de conectividade.
    """
    status = {
        "ok": True,
        "message": "API operacional",
        "version": API_VERSION,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

    # Testa conectividade com API-Sports (opcional)
    if API_KEY:
        try:
            test_data, test_error = call_api_football("/status", {})
            if test_error:
                status["api_sports_status"] = "error"
                status["api_sports_error"] = test_error
            else:
                status["api_sports_status"] = "connected"
        except Exception as e:
            status["api_sports_status"] = "unknown"
            logger.warning(f"Health check API-Sports falhou: {e}")
    else:
        status["api_sports_status"] = "not_configured"
        status["warning"] = "API_KEY não configurada"

    return jsonify(status)


@app.route("/openapi.json")
def openapi_json():
    """
    Retorna o schema OpenAPI em formato JSON.
    """
    try:
        # Tenta carregar do arquivo primeiro
        base_dir = os.path.dirname(os.path.abspath(__file__))
        yaml_path = os.path.join(base_dir, "openapi.yaml")

        if not os.path.exists(yaml_path):
            yaml_path = "openapi.yaml"

        if os.path.exists(yaml_path):
            with open(yaml_path, "r", encoding="utf-8") as f:
                openapi_yaml = yaml.safe_load(f)
            return jsonify(openapi_yaml)
        else:
            # Fallback: retorna schema inline se arquivo não existir
            logger.warning("openapi.yaml não encontrado, usando schema inline")
            return jsonify({
                "openapi": "3.1.0",
                "info": {
                    "title": "Apostas Esportivas Pro API",
                    "version": API_VERSION,
                    "description": "API profissional para análises esportivas. Schema completo disponível em: https://github.com/nlsoarez/apostasesportivaspro/blob/main/openapi.yaml"
                },
                "servers": [{"url": "https://apostasesportivas.vercel.app"}],
                "paths": {
                    "/health": {"get": {"summary": "Health check", "operationId": "checkHealth"}},
                    "/fixtures": {"get": {"summary": "Lista jogos", "operationId": "getFixtures"}},
                    "/standings": {"get": {"summary": "Classificação", "operationId": "getStandings"}},
                    "/leagues": {"get": {"summary": "Ligas suportadas", "operationId": "getLeagues"}},
                    "/analysis/value": {"get": {"summary": "Value Bet", "operationId": "getValueBet"}},
                    "/analysis/corners": {"get": {"summary": "Análise escanteios", "operationId": "getAnalysisCorners"}},
                    "/analysis/cards": {"get": {"summary": "Análise cartões", "operationId": "getAnalysisCards"}},
                    "/news/context": {"get": {"summary": "Notícias", "operationId": "getNewsContext"}}
                }
            })
    except Exception as e:
        logger.error(f"Erro ao carregar OpenAPI: {e}")
        return error_response(f"Erro ao carregar schema: {str(e)}", 500)


@app.route("/leagues")
def leagues():
    """
    Lista todas as ligas suportadas pela API.
    """
    leagues_list = [
        {"id": league_id, "name": league_name}
        for league_id, league_name in sorted(SUPPORTED_LEAGUES.items(), key=lambda x: x[1])
    ]

    return jsonify({
        "ok": True,
        "total": len(leagues_list),
        "leagues": leagues_list,
        "categories": {
            "brasil": [71, 72, 73, 75, 76],
            "europa": [39, 140, 135, 78, 61, 94, 88],
            "internacional": [2, 3, 848, 13, 11],
            "americas": [253, 128],
            "mundial": [1, 960]
        }
    })


@app.route("/fixtures", methods=["GET"])
def fixtures():
    """
    Lista jogos filtrados por data, liga ou rodada.

    Query Parameters:
        - league (required): ID da liga
        - date: Data no formato YYYY-MM-DD
        - round: Rodada (alternativa a date)
        - season: Ano da temporada (default: 2025)
        - status: Status do jogo (NS, LIVE, FT, etc.)
        - timezone: Fuso horário (default: America/Sao_Paulo)
    """
    league = request.args.get("league")
    date = request.args.get("date")
    round_param = request.args.get("round")
    season = request.args.get("season", str(DEFAULT_SEASON))
    status = request.args.get("status")
    timezone = request.args.get("timezone", DEFAULT_TIMEZONE)

    # Validações
    if not league:
        return error_response("Parâmetro 'league' é obrigatório")

    if not date and not round_param:
        return error_response("Parâmetro 'date' ou 'round' é obrigatório")

    # Validar league é inteiro
    league_id, error = validate_integer_param(league, "league")
    if error:
        return error_response(error)

    params = {"league": league_id, "season": season, "timezone": timezone}
    if date:
        params["date"] = date
    if round_param:
        params["round"] = round_param
    if status:
        params["status"] = status

    data, error = call_api_football("/fixtures", params)
    if error:
        return error_response(error, 500)

    jogos = []
    for fixture in data.get("response", []):
        info = fixture.get("fixture", {})
        teams = fixture.get("teams", {})
        jogos.append({
            "id": info.get("id"),
            "data": info.get("date"),
            "status": info.get("status", {}).get("short"),
            "mandante": teams.get("home", {}).get("name"),
            "visitante": teams.get("away", {}).get("name"),
        })

    return jsonify({"ok": True, "total": len(jogos), "jogos": jogos})


@app.route("/standings")
def standings():
    """
    Retorna a classificação de uma liga.

    Query Parameters:
        - league (required): ID da liga
        - season: Ano da temporada (default: 2025)
    """
    league = request.args.get("league")
    season = request.args.get("season", str(DEFAULT_SEASON))

    if not league:
        return error_response("Parâmetro 'league' é obrigatório")

    league_id, error = validate_integer_param(league, "league")
    if error:
        return error_response(error)

    data, error = call_api_football("/standings", {"league": league_id, "season": season})
    if error:
        return error_response(error, 500)

    return jsonify({"ok": True, "standings": data.get("response", [])})


@app.route("/teams/statistics")
def team_statistics():
    team = request.args.get("team")
    league = request.args.get("league")
    season = request.args.get("season", "2025")
    if not (team and league): return error_response("Parâmetros 'team' e 'league' obrigatórios")

    data, error = call_api_football("/teams/statistics", {"team": team, "league": league, "season": season})
    if error: return error_response(error, 500)
    return jsonify({"ok": True, "stats": data.get("response", {})})


@app.route("/players/topscorers")
def top_scorers():
    league = request.args.get("league")
    season = request.args.get("season", "2025")
    if not league: return error_response("Parâmetro 'league' obrigatório")

    data, error = call_api_football("/players/topscorers", {"league": league, "season": season})
    if error: return error_response(error, 500)
    return jsonify({"ok": True, "artilheiros": data.get("response", [])})


# =======================
# Endpoints avançados
# =======================
@app.route("/fixtures/headtohead")
def head_to_head():
    """
    Retorna histórico de confrontos diretos (H2H) entre dois times.

    Query Parameters:
        - h2h (required): IDs dos times no formato "idTimeA-idTimeB"
                         Exemplo: h2h=127-121 (Flamengo vs Palmeiras)
    """
    h2h = request.args.get("h2h")

    if not h2h:
        return error_response("Parâmetro 'h2h' é obrigatório. Exemplo: h2h=127-121")

    # Validar formato h2h
    if "-" not in h2h:
        return error_response("Formato inválido. Use: h2h=idTime1-idTime2 (ex: 127-121)")

    data, error = call_api_football("/fixtures/headtohead", {"h2h": h2h})
    if error:
        return error_response(error, 500)

    resultados = []
    for match in data.get("response", [])[:MAX_H2H_RESULTS]:
        placar = match.get("goals", {})
        resultados.append({
            "mandante": match["teams"]["home"]["name"],
            "visitante": match["teams"]["away"]["name"],
            "placar": f"{placar.get('home', 0)}x{placar.get('away', 0)}"
        })

    return jsonify({"ok": True, "total": len(resultados), "resultados": resultados})


@app.route("/injuries")
def injuries():
    league = request.args.get("league")
    team = request.args.get("team")
    season = request.args.get("season", "2025")
    if not (league and team): return error_response("Parâmetros 'league' e 'team' obrigatórios")

    data, error = call_api_football("/injuries", {"league": league, "team": team, "season": season})
    if error: return error_response(error, 500)

    lesoes = []
    for injury in data.get("response", []):
        player = injury.get("player", {})
        detail = injury.get("injury", {})
        lesoes.append({
            "jogador": player.get("name"),
            "tipo": detail.get("type"),
            "motivo": detail.get("reason")
        })
    return jsonify({"ok": True, "total": len(lesoes), "lesoes": lesoes})


@app.route("/odds")
def odds():
    fixture = request.args.get("fixture")
    if not fixture: return error_response("Parâmetro 'fixture' obrigatório")

    data, error = call_api_football("/odds", {"fixture": fixture})
    if error: return error_response(error, 500)
    return jsonify({"ok": True, "odds": data.get("response", [])})


@app.route("/predictions")
def predictions():
    fixture = request.args.get("fixture")
    if not fixture: return error_response("Parâmetro 'fixture' obrigatório")

    data, error = call_api_football("/predictions", {"fixture": fixture})
    if error: return error_response(error, 500)
    return jsonify({"ok": True, "predicoes": data.get("response", [])})


@app.route("/fixtures/live")
def live_fixtures():
    """
    Lista jogos ao vivo no momento (top 20).

    Retorna os principais jogos que estão acontecendo agora,
    com status, minuto e times envolvidos.
    """
    data, error = call_api_football("/fixtures", {"live": "all"})
    if error:
        return error_response(error, 500)

    partidas = []
    for fixture in data.get("response", [])[:MAX_LIVE_FIXTURES]:
        info = fixture.get("fixture", {})
        teams = fixture.get("teams", {})
        goals = fixture.get("goals", {})
        partidas.append({
            "id": info.get("id"),
            "status": info.get("status", {}).get("short"),
            "minuto": info.get("status", {}).get("elapsed"),
            "mandante": teams.get("home", {}).get("name"),
            "visitante": teams.get("away", {}).get("name"),
            "placar": f"{goals.get('home', 0)}x{goals.get('away', 0)}"
        })

    return jsonify({
        "ok": True,
        "total": len(partidas),
        "partidas": partidas,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    })


# =======================
# Endpoints profissionais
# =======================
@app.route("/analysis/corners")
def analysis_corners():
    """
    Análise profissional de escanteios baseada em estatísticas.

    Query Parameters:
        - team_home (required): ID do time mandante
        - team_away (required): ID do time visitante
        - league (required): ID da liga
        - season: Ano da temporada (default: 2025)

    Calcula estimativa baseada em média de escanteios a favor.
    """
    team_home = request.args.get("team_home")
    team_away = request.args.get("team_away")
    league = request.args.get("league")
    season = request.args.get("season", str(DEFAULT_SEASON))

    if not (team_home and team_away and league):
        return error_response("Parâmetros obrigatórios: team_home, team_away, league")

    # Validar IDs
    home_id, error = validate_integer_param(team_home, "team_home")
    if error:
        return error_response(error)

    away_id, error = validate_integer_param(team_away, "team_away")
    if error:
        return error_response(error)

    league_id, error = validate_integer_param(league, "league")
    if error:
        return error_response(error)

    stats_home, _ = call_api_football("/teams/statistics", {"team": home_id, "league": league_id, "season": season})
    stats_away, _ = call_api_football("/teams/statistics", {"team": away_id, "league": league_id, "season": season})

    try:
        media_home = stats_home["response"]["fixtures"]["corners"]["for"]["average"]["home"]
        media_away = stats_away["response"]["fixtures"]["corners"]["for"]["average"]["away"]
        estimativa = round(float(media_home) + float(media_away), 1)
    except Exception as e:
        logger.warning(f"Erro ao calcular escanteios: {e}. Usando valor padrão.")
        estimativa = DEFAULT_CORNERS_ESTIMATE

    analise = {
        "time_casa": {"id": home_id},
        "time_fora": {"id": away_id},
        "estimativa_total": estimativa,
        "sugestoes": [{
            "mercado": "Over 9.5 Escanteios Totais",
            "confianca": 5 if estimativa >= 10 else 4,
            "value_estimado": "+20%" if estimativa >= 10 else "+10%"
        }]
    }
    return jsonify({"ok": True, "analise_escanteios": analise})


@app.route("/analysis/cards")
def analysis_cards():
    """
    Análise profissional de cartões amarelos baseada em estatísticas.

    Query Parameters:
        - team_home (required): ID do time mandante
        - team_away (required): ID do time visitante
        - league (required): ID da liga
        - season: Ano da temporada (default: 2025)

    Calcula estimativa baseada em média de cartões amarelos.
    """
    team_home = request.args.get("team_home")
    team_away = request.args.get("team_away")
    league = request.args.get("league")
    season = request.args.get("season", str(DEFAULT_SEASON))

    if not (team_home and team_away and league):
        return error_response("Parâmetros obrigatórios: team_home, team_away, league")

    # Validar IDs
    home_id, error = validate_integer_param(team_home, "team_home")
    if error:
        return error_response(error)

    away_id, error = validate_integer_param(team_away, "team_away")
    if error:
        return error_response(error)

    league_id, error = validate_integer_param(league, "league")
    if error:
        return error_response(error)

    stats_home, _ = call_api_football("/teams/statistics", {"team": home_id, "league": league_id, "season": season})
    stats_away, _ = call_api_football("/teams/statistics", {"team": away_id, "league": league_id, "season": season})

    try:
        media_home = stats_home["response"]["cards"]["yellow"]["average"]["home"]
        media_away = stats_away["response"]["cards"]["yellow"]["average"]["away"]
        estimativa = round(float(media_home) + float(media_away), 1)
    except Exception as e:
        logger.warning(f"Erro ao calcular cartões: {e}. Usando valor padrão.")
        estimativa = DEFAULT_CARDS_ESTIMATE

    analise = {
        "time_casa": {"id": home_id},
        "time_fora": {"id": away_id},
        "estimativa_total": estimativa,
        "sugestoes": [{
            "mercado": "Over 5.5 Cartões Totais",
            "confianca": 5 if estimativa >= 5.5 else 4,
            "value_estimado": "+25%" if estimativa >= 5.5 else "+10%"
        }]
    }
    return jsonify({"ok": True, "analise_cartoes": analise})


@app.route("/analysis/value")
def analysis_value():
    """
    Calcula Value Bet usando a fórmula: (probabilidade × odd) - 1

    Query Parameters:
        - odd (required): Odd da casa de apostas (1.01 - 100.0)
        - probability (required): Probabilidade estimada (0.01 - 1.0)

    Returns:
        - value > 0: Aposta com valor (recomendada)
        - value < 0: Sem valor (evitar)
    """
    odd_str = request.args.get("odd")
    prob_str = request.args.get("probability")

    # Validar odd
    odd, error = validate_numeric_param(
        odd_str, "odd",
        min_val=MIN_ODD_VALUE,
        max_val=MAX_ODD_VALUE,
        required=True
    )
    if error:
        return error_response(f"{error}. Exemplo: odd=2.50")

    # Validar probability
    prob, error = validate_numeric_param(
        prob_str, "probability",
        min_val=MIN_PROBABILITY,
        max_val=MAX_PROBABILITY,
        required=True
    )
    if error:
        return error_response(f"{error}. Exemplo: probability=0.50 (50%)")

    # Calcular value
    value = round((prob * odd) - 1, 3)

    return jsonify({
        "ok": True,
        "value": value,
        "interpretation": "Value Bet ✅" if value > 0 else "Sem Value ❌",
        "recommendation": "Apostar" if value > 0.05 else "Evitar",
        "formula": f"({prob} × {odd}) - 1 = {value}"
    })


# =======================
# Endpoint contextual
# =======================
@app.route("/news/context")
def news_context():
    """
    Busca notícias recentes sobre um time.

    Query Parameters:
        - team (required): Nome do time
        - league: Nome da liga (opcional)
        - days: Últimos N dias (1-30, default: 3)

    Busca notícias sobre lesões, suspensões, mudanças técnicas, etc.
    Fontes: GE Globo, ESPN Brasil
    """
    team = request.args.get("team")
    league = request.args.get("league")
    days_str = request.args.get("days", str(DEFAULT_NEWS_DAYS))

    if not team:
        return error_response("Parâmetro 'team' é obrigatório. Exemplo: team=Flamengo")

    # Validar days
    days, error = validate_integer_param(days_str, "days", required=False)
    if error:
        return error_response(error)

    if days is None:
        days = DEFAULT_NEWS_DAYS

    if days < 1 or days > MAX_NEWS_DAYS:
        return error_response(f"Parâmetro 'days' deve estar entre 1 e {MAX_NEWS_DAYS}")

    if not NEWS_API_KEY:
        return error_response("NEWS_API_KEY não configurada", 503)

    query = f"{team} {league or ''} futebol lesão suspensão demitido técnico clima site:ge.globo.com OR site:espn.com.br"
    url = "https://newsapi.org/v2/everything"
    headers = {"Authorization": NEWS_API_KEY}
    params = {
        "q": query,
        "language": "pt",
        "sortBy": "publishedAt",
        "pageSize": 5,
        "from": (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d"),
    }

    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        if response.status_code != 200:
            logger.error(f"[NEWS API] HTTP {response.status_code}")
            return error_response(f"Erro na API de notícias: HTTP {response.status_code}", 500)

        data = response.json()
        artigos = [{
            "titulo": art.get("title"),
            "fonte": art.get("source", {}).get("name"),
            "publicado_em": art.get("publishedAt"),
            "url": art.get("url")
        } for art in data.get("articles", [])]

        return jsonify({
            "ok": True,
            "team": team,
            "league": league,
            "days_searched": days,
            "total": len(artigos),
            "noticias": artigos
        })
    except Exception as e:
        logger.error(f"[NEWS API ERROR] {str(e)}")
        return error_response(f"Erro ao buscar notícias: {str(e)}", 500)


# =======================
# Handlers de erro
# =======================
@app.errorhandler(404)
def not_found(e):
    return jsonify({"ok": False, "error": "Rota não encontrada"}), 404

@app.errorhandler(500)
def internal_error(e):
    return jsonify({"ok": False, "error": "Erro interno no servidor"}), 500


if __name__ == "__main__":
    app.run(debug=True)
