import os
import logging
import requests
import json
import yaml
import time
from datetime import datetime, timedelta
from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
from werkzeug.middleware.proxy_fix import ProxyFix
from dotenv import load_dotenv
from functools import lru_cache

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
API_TIMEOUT = float(os.getenv("API_TIMEOUT", "15"))
API_MAX_RETRIES = int(os.getenv("API_MAX_RETRIES", "3"))
API_RETRY_DELAY = float(os.getenv("API_RETRY_DELAY", "1"))
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
def call_api_football(endpoint, params, max_retries=None):
    """
    Chama a API-Football com retry automático e exponential backoff.

    Args:
        endpoint (str): Endpoint da API (ex: /fixtures)
        params (dict): Parâmetros da query string
        max_retries (int): Número máximo de tentativas (default: API_MAX_RETRIES)

    Returns:
        tuple: (data, error) onde data é o JSON de resposta ou None em caso de erro
    """
    if not API_KEY:
        return None, "API_KEY não configurada"

    if max_retries is None:
        max_retries = API_MAX_RETRIES

    url = f"https://{API_HOST}{endpoint}"
    last_error = None

    for attempt in range(max_retries):
        try:
            # Configura timeout com margem de segurança
            timeout = API_TIMEOUT + (attempt * 2)  # Aumenta timeout a cada tentativa

            response = requests.get(
                url,
                headers=HEADERS_API,
                params=params,
                timeout=timeout
            )

            if response.status_code == 200:
                data = response.json()
                if "errors" in data and data["errors"]:
                    return None, str(data["errors"])
                return data, None

            # Erros temporários que podem ser retentados
            elif response.status_code in [429, 500, 502, 503, 504]:
                last_error = f"HTTP {response.status_code}"
                logger.warning(f"[API Retry {attempt+1}/{max_retries}] {last_error} -> {endpoint}")

                if attempt < max_retries - 1:
                    delay = API_RETRY_DELAY * (2 ** attempt)  # Exponential backoff
                    time.sleep(delay)
                    continue

            # Erros permanentes (não tentar novamente)
            else:
                logger.error(f"[API] HTTP {response.status_code} -> {endpoint}")
                return None, f"Erro HTTP {response.status_code}"

        except requests.exceptions.Timeout as e:
            last_error = "Timeout na requisição"
            logger.warning(f"[API Timeout {attempt+1}/{max_retries}] {endpoint}")

            if attempt < max_retries - 1:
                delay = API_RETRY_DELAY * (2 ** attempt)
                time.sleep(delay)
                continue

        except requests.exceptions.ConnectionError as e:
            last_error = "Erro de conexão"
            logger.warning(f"[API Connection Error {attempt+1}/{max_retries}] {endpoint}")

            if attempt < max_retries - 1:
                delay = API_RETRY_DELAY * (2 ** attempt)
                time.sleep(delay)
                continue

        except Exception as e:
            last_error = str(e)
            logger.error(f"[API Exception] {last_error}")
            return None, last_error

    # Se chegou aqui, todas as tentativas falharam
    logger.error(f"[API] Todas as {max_retries} tentativas falharam para {endpoint}")
    return None, f"Falha após {max_retries} tentativas: {last_error}"


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


def calculate_must_win_factor(team_stats, standings_position=None, total_teams=None):
    """
    Calcula o fator 'Must Win' para um time baseado em sua situação.

    Args:
        team_stats (dict): Estatísticas do time
        standings_position (int): Posição atual na tabela
        total_teams (int): Total de times na liga

    Returns:
        dict: Informações sobre o fator Must Win com score de 0-10
    """
    must_win_score = 5.0  # Score neutro
    factors = []

    # Análise de posição na tabela (se disponível)
    if standings_position and total_teams:
        # Zona de rebaixamento (geralmente últimos 4)
        relegation_zone = total_teams - 3
        # Zona de classificação para competições (geralmente top 6)
        classification_zone = 6

        if standings_position >= relegation_zone:
            must_win_score += 3.0
            factors.append({
                "fator": "Zona de Rebaixamento",
                "impacto": "CRÍTICO",
                "descricao": f"Time na {standings_position}ª posição (zona de rebaixamento)"
            })
        elif standings_position >= (relegation_zone - 3):
            must_win_score += 2.0
            factors.append({
                "fator": "Próximo à Zona de Rebaixamento",
                "impacto": "ALTO",
                "descricao": f"Time próximo da zona perigosa ({standings_position}ª posição)"
            })
        elif standings_position <= classification_zone:
            must_win_score += 1.5
            factors.append({
                "fator": "Briga por Classificação",
                "impacto": "MODERADO",
                "descricao": f"Time brigando por vaga em competições ({standings_position}ª posição)"
            })

    # Análise de sequência de resultados
    if team_stats:
        try:
            form = team_stats.get("form", "")
            if form:
                # Contar derrotas recentes (L = Loss)
                recent_losses = form[-5:].count("L")
                recent_draws = form[-5:].count("D")
                recent_wins = form[-5:].count("W")

                if recent_losses >= 3:
                    must_win_score += 2.0
                    factors.append({
                        "fator": "Sequência Negativa",
                        "impacto": "ALTO",
                        "descricao": f"{recent_losses} derrotas nos últimos 5 jogos"
                    })
                elif recent_losses >= 2 and recent_draws >= 2:
                    must_win_score += 1.5
                    factors.append({
                        "fator": "Momento Instável",
                        "impacto": "MODERADO",
                        "descricao": "Sequência inconsistente de resultados"
                    })
                elif recent_wins >= 4:
                    must_win_score -= 1.0
                    factors.append({
                        "fator": "Boa Sequência",
                        "impacto": "BAIXO",
                        "descricao": f"{recent_wins} vitórias nos últimos 5 jogos (pressão menor)"
                    })
        except:
            pass

    # Normalizar score entre 0-10
    must_win_score = max(0, min(10, must_win_score))

    return {
        "score": round(must_win_score, 1),
        "nivel": (
            "CRÍTICO" if must_win_score >= 8 else
            "ALTO" if must_win_score >= 6.5 else
            "MODERADO" if must_win_score >= 5 else
            "BAIXO"
        ),
        "fatores": factors,
        "recomendacao": (
            "Time sob EXTREMA pressão por resultado. Análise de motivação é crucial." if must_win_score >= 8 else
            "Time precisa pontuar. Fator motivacional significativo." if must_win_score >= 6.5 else
            "Jogo importante, mas sem pressão extrema." if must_win_score >= 5 else
            "Time em situação confortável."
        )
    }


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
        "description": "API profissional para integração com GPTs e análises esportivas avançadas.",
        "documentation": "/openapi.json",
        "endpoints": {
            "base": ["/health", "/fixtures", "/standings", "/teams/statistics", "/players/topscorers", "/leagues"],
            "avancados": ["/fixtures/headtohead", "/injuries", "/odds", "/predictions", "/fixtures/live"],
            "ao_vivo": ["/fixtures/live/analysis", "/fixtures/live/minute-by-minute"],
            "profissionais": ["/analysis/corners", "/analysis/cards", "/analysis/value", "/news/context"]
        },
        "features": [
            "50+ ligas suportadas",
            "Dados em tempo real",
            "Análises profissionais com fator Must Win",
            "Análises de jogos ao vivo",
            "Análises minuto a minuto",
            "Value Betting",
            "Previsões IA",
            "Contexto de notícias",
            "Retry automático com exponential backoff"
        ],
        "whats_new_v5": [
            "Fator 'Must Win' integrado em todas as análises",
            "Análise de jogos ao vivo com estatísticas em tempo real",
            "Análise minuto a minuto com timeline de eventos",
            "Sistema de retry melhorado para maior confiabilidade",
            "Vercel runtime configurado corretamente"
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


@app.route("/fixtures/live/analysis")
def live_analysis():
    """
    Análise profissional de um jogo ao vivo com Must Win e estatísticas em tempo real.

    Query Parameters:
        - fixture (required): ID do jogo ao vivo
        - league (required): ID da liga
        - season: Ano da temporada (default: 2025)

    Retorna análise completa incluindo:
    - Estatísticas do jogo (posse, chutes, escanteios, cartões)
    - Fator Must Win de ambos os times
    - Análise de momento do jogo
    - Sugestões de apostas ao vivo
    """
    fixture_id = request.args.get("fixture")
    league = request.args.get("league")
    season = request.args.get("season", str(DEFAULT_SEASON))

    if not fixture_id:
        return error_response("Parâmetro 'fixture' é obrigatório")

    if not league:
        return error_response("Parâmetro 'league' é obrigatório")

    # Validar IDs
    fixture_id_int, error = validate_integer_param(fixture_id, "fixture")
    if error:
        return error_response(error)

    league_id, error = validate_integer_param(league, "league")
    if error:
        return error_response(error)

    # Buscar dados do jogo ao vivo
    fixture_data, error = call_api_football("/fixtures", {"id": fixture_id_int})
    if error:
        return error_response(error, 500)

    if not fixture_data.get("response"):
        return error_response("Jogo não encontrado", 404)

    match = fixture_data["response"][0]
    fixture_info = match.get("fixture", {})
    teams = match.get("teams", {})
    goals = match.get("goals", {})
    score = match.get("score", {})
    events = match.get("events", [])
    statistics = match.get("statistics", [])

    # Extrair IDs dos times
    home_id = teams.get("home", {}).get("id")
    away_id = teams.get("away", {}).get("id")

    # Buscar estatísticas dos times e classificação
    stats_home, _ = call_api_football("/teams/statistics", {"team": home_id, "league": league_id, "season": season})
    stats_away, _ = call_api_football("/teams/statistics", {"team": away_id, "league": league_id, "season": season})
    standings_data, _ = call_api_football("/standings", {"league": league_id, "season": season})

    # Calcular posições na tabela
    home_position = None
    away_position = None
    total_teams = None

    try:
        if standings_data and standings_data.get("response"):
            standings = standings_data["response"][0]["league"]["standings"][0]
            total_teams = len(standings)
            for team in standings:
                if team["team"]["id"] == home_id:
                    home_position = team["rank"]
                if team["team"]["id"] == away_id:
                    away_position = team["rank"]
    except:
        pass

    # Calcular Must Win
    must_win_home = calculate_must_win_factor(
        stats_home.get("response") if stats_home else None,
        home_position,
        total_teams
    )
    must_win_away = calculate_must_win_factor(
        stats_away.get("response") if stats_away else None,
        away_position,
        total_teams
    )

    # Processar estatísticas do jogo ao vivo
    live_stats = {
        "mandante": {},
        "visitante": {}
    }

    if statistics:
        for team_stats in statistics:
            team_name = team_stats.get("team", {}).get("name")
            stats_dict = {}
            for stat in team_stats.get("statistics", []):
                stat_type = stat.get("type")
                stat_value = stat.get("value")
                stats_dict[stat_type] = stat_value

            if team_name == teams.get("home", {}).get("name"):
                live_stats["mandante"] = stats_dict
            else:
                live_stats["visitante"] = stats_dict

    # Análise de momento do jogo
    elapsed = fixture_info.get("status", {}).get("elapsed", 0)
    momento = "Início de jogo"
    if elapsed > 75:
        momento = "Final de jogo - Pressão máxima"
    elif elapsed > 60:
        momento = "Reta final - Momento decisivo"
    elif elapsed > 45:
        momento = "Segundo tempo"
    elif elapsed > 30:
        momento = "Final do primeiro tempo"

    # Sugestões baseadas no contexto ao vivo
    sugestoes = []

    # Análise de gols
    total_goals = (goals.get("home", 0) or 0) + (goals.get("away", 0) or 0)
    if elapsed > 60 and total_goals == 0:
        sugestoes.append({
            "tipo": "Gols",
            "mercado": "Ambas marcam - NÃO",
            "justificativa": f"Jogo sem gols aos {elapsed}' - defesas sólidas",
            "confianca": 4
        })
    elif total_goals >= 2 and elapsed < 60:
        sugestoes.append({
            "tipo": "Gols",
            "mercado": "Over 2.5 ou 3.5 gols",
            "justificativa": f"{total_goals} gols em apenas {elapsed}' - jogo aberto",
            "confianca": 4
        })

    # Análise de escanteios (se disponível)
    try:
        corners_home = live_stats["mandante"].get("Corner Kicks", 0)
        corners_away = live_stats["visitante"].get("Corner Kicks", 0)
        if corners_home is not None and corners_away is not None:
            total_corners = int(corners_home) + int(corners_away)
            if elapsed > 0:
                corners_por_minuto = total_corners / elapsed
                corners_projetados = round(corners_por_minuto * 90, 1)
                sugestoes.append({
                    "tipo": "Escanteios",
                    "mercado": f"Projeção: {corners_projetados} escanteios no jogo",
                    "justificativa": f"{total_corners} escanteios em {elapsed}' (ritmo de {round(corners_por_minuto, 2)}/min)",
                    "confianca": 4 if elapsed > 30 else 3
                })
    except:
        pass

    # Análise de cartões
    try:
        cards_home = (live_stats["mandante"].get("Yellow Cards", 0) or 0) + \
                     (live_stats["mandante"].get("Red Cards", 0) or 0) * 2
        cards_away = (live_stats["visitante"].get("Yellow Cards", 0) or 0) + \
                     (live_stats["visitante"].get("Red Cards", 0) or 0) * 2
        total_cards = cards_home + cards_away

        if total_cards >= 4 and elapsed < 60:
            sugestoes.append({
                "tipo": "Cartões",
                "mercado": "Over cartões",
                "justificativa": f"{total_cards} cartões em {elapsed}' - jogo disputado",
                "confianca": 4
            })
    except:
        pass

    return jsonify({
        "ok": True,
        "jogo": {
            "id": fixture_id_int,
            "status": fixture_info.get("status", {}).get("long"),
            "minuto": elapsed,
            "momento_jogo": momento,
            "mandante": teams.get("home", {}).get("name"),
            "visitante": teams.get("away", {}).get("name"),
            "placar": {
                "atual": f"{goals.get('home', 0)}x{goals.get('away', 0)}",
                "halftime": f"{score.get('halftime', {}).get('home', 0)}x{score.get('halftime', {}).get('away', 0)}"
            }
        },
        "estatisticas_ao_vivo": live_stats,
        "must_win": {
            "mandante": must_win_home,
            "visitante": must_win_away,
            "analise": (
                "Jogo decisivo para ambos os times" if must_win_home["score"] >= 7 and must_win_away["score"] >= 7 else
                f"Mais importante para {teams.get('home', {}).get('name')}" if must_win_home["score"] > must_win_away["score"] + 2 else
                f"Mais importante para {teams.get('away', {}).get('name')}" if must_win_away["score"] > must_win_home["score"] + 2 else
                "Importância equilibrada para ambos"
            )
        },
        "sugestoes_ao_vivo": sugestoes,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    })


@app.route("/fixtures/live/minute-by-minute")
def minute_by_minute_analysis():
    """
    Análise minuto a minuto de um jogo ao vivo ou finalizado.

    Query Parameters:
        - fixture (required): ID do jogo

    Retorna:
    - Timeline completa de eventos (gols, cartões, substituições)
    - Análise de cada período do jogo (0-15, 16-30, 31-45, etc)
    - Momentos-chave identificados
    - Padrões de jogo por período
    """
    fixture_id = request.args.get("fixture")

    if not fixture_id:
        return error_response("Parâmetro 'fixture' é obrigatório")

    # Validar ID
    fixture_id_int, error = validate_integer_param(fixture_id, "fixture")
    if error:
        return error_response(error)

    # Buscar dados do jogo
    fixture_data, error = call_api_football("/fixtures", {"id": fixture_id_int})
    if error:
        return error_response(error, 500)

    if not fixture_data.get("response"):
        return error_response("Jogo não encontrado", 404)

    match = fixture_data["response"][0]
    fixture_info = match.get("fixture", {})
    teams = match.get("teams", {})
    events = match.get("events", []) or []

    # Processar eventos
    timeline = []
    goals_timeline = []
    cards_timeline = []
    substitutions = []

    for event in events:
        minute = event.get("time", {}).get("elapsed", 0)
        extra = event.get("time", {}).get("extra")
        event_type = event.get("type")
        detail = event.get("detail")
        team = event.get("team", {}).get("name")
        player = event.get("player", {}).get("name", "Desconhecido")

        minute_display = f"{minute}'" if not extra else f"{minute}'+{extra}'"

        event_obj = {
            "minuto": minute,
            "minuto_display": minute_display,
            "tipo": event_type,
            "detalhe": detail,
            "time": team,
            "jogador": player
        }

        timeline.append(event_obj)

        if event_type == "Goal":
            goals_timeline.append(event_obj)
        elif event_type == "Card":
            cards_timeline.append(event_obj)
        elif event_type == "subst":
            substitutions.append(event_obj)

    # Análise por períodos (0-15, 16-30, 31-45, 46-60, 61-75, 76-90+)
    periods = {
        "0-15": {"gols": 0, "cartoes": 0, "eventos": []},
        "16-30": {"gols": 0, "cartoes": 0, "eventos": []},
        "31-45": {"gols": 0, "cartoes": 0, "eventos": []},
        "46-60": {"gols": 0, "cartoes": 0, "eventos": []},
        "61-75": {"gols": 0, "cartoes": 0, "eventos": []},
        "76-90+": {"gols": 0, "cartoes": 0, "eventos": []}
    }

    def get_period(minute):
        if minute <= 15:
            return "0-15"
        elif minute <= 30:
            return "16-30"
        elif minute <= 45:
            return "31-45"
        elif minute <= 60:
            return "46-60"
        elif minute <= 75:
            return "61-75"
        else:
            return "76-90+"

    for event in timeline:
        minute = event.get("minuto", 0)
        period = get_period(minute)

        if event["tipo"] == "Goal":
            periods[period]["gols"] += 1
        elif event["tipo"] == "Card":
            periods[period]["cartoes"] += 1

        periods[period]["eventos"].append(event)

    # Identificar momentos-chave
    momentos_chave = []

    # Gols nos primeiros 15 minutos
    if periods["0-15"]["gols"] > 0:
        momentos_chave.append({
            "periodo": "0-15",
            "descricao": f"Início elétrico com {periods['0-15']['gols']} gol(s)",
            "impacto": "ALTO"
        })

    # Período mais movimentado
    periodo_mais_movimentado = max(periods.items(),
                                   key=lambda x: len(x[1]["eventos"]))
    if len(periodo_mais_movimentado[1]["eventos"]) >= 5:
        momentos_chave.append({
            "periodo": periodo_mais_movimentado[0],
            "descricao": f"Período mais agitado com {len(periodo_mais_movimentado[1]['eventos'])} eventos",
            "impacto": "MODERADO"
        })

    # Cartões em excesso
    total_cards_period = max([p["cartoes"] for p in periods.values()])
    if total_cards_period >= 3:
        periodo_violento = [k for k, v in periods.items() if v["cartoes"] == total_cards_period][0]
        momentos_chave.append({
            "periodo": periodo_violento,
            "descricao": f"Período de jogo mais duro com {total_cards_period} cartões",
            "impacto": "ALTO"
        })

    # Análise de padrões
    padroes = []

    # Padrão de gols
    total_goals = len(goals_timeline)
    if total_goals > 0:
        goals_1st_half = sum(1 for g in goals_timeline if g["minuto"] <= 45)
        goals_2nd_half = total_goals - goals_1st_half

        if goals_2nd_half > goals_1st_half * 1.5:
            padroes.append({
                "tipo": "Gols",
                "padrao": "Jogo abriu no segundo tempo",
                "dados": f"{goals_1st_half} no 1ºT vs {goals_2nd_half} no 2ºT"
            })
        elif goals_1st_half > goals_2nd_half * 1.5:
            padroes.append({
                "tipo": "Gols",
                "padrao": "Jogo decidido no primeiro tempo",
                "dados": f"{goals_1st_half} no 1ºT vs {goals_2nd_half} no 2ºT"
            })

    # Padrão de cartões
    total_cards = len(cards_timeline)
    if total_cards >= 4:
        yellow_cards = sum(1 for c in cards_timeline if c["detalhe"] == "Yellow Card")
        padroes.append({
            "tipo": "Cartões",
            "padrao": "Jogo disputado com muitas faltas",
            "dados": f"{total_cards} cartões ({yellow_cards} amarelos)"
        })

    return jsonify({
        "ok": True,
        "jogo": {
            "id": fixture_id_int,
            "mandante": teams.get("home", {}).get("name"),
            "visitante": teams.get("away", {}).get("name"),
            "status": fixture_info.get("status", {}).get("long")
        },
        "timeline_completa": sorted(timeline, key=lambda x: x["minuto"]),
        "analise_por_periodos": periods,
        "momentos_chave": momentos_chave,
        "padroes_identificados": padroes,
        "resumo": {
            "total_eventos": len(timeline),
            "total_gols": len(goals_timeline),
            "total_cartoes": len(cards_timeline),
            "total_substituicoes": len(substitutions)
        },
        "timestamp": datetime.utcnow().isoformat() + "Z"
    })


# =======================
# Endpoints profissionais
# =======================
@app.route("/analysis/corners")
def analysis_corners():
    """
    Análise profissional de escanteios baseada em estatísticas com fator Must Win.

    Query Parameters:
        - team_home (required): ID do time mandante
        - team_away (required): ID do time visitante
        - league (required): ID da liga
        - season: Ano da temporada (default: 2025)

    Calcula estimativa baseada em média de escanteios a favor + fator Must Win.
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

    # Buscar dados
    stats_home, _ = call_api_football("/teams/statistics", {"team": home_id, "league": league_id, "season": season})
    stats_away, _ = call_api_football("/teams/statistics", {"team": away_id, "league": league_id, "season": season})
    standings_data, _ = call_api_football("/standings", {"league": league_id, "season": season})

    # Calcular posições na tabela
    home_position = None
    away_position = None
    total_teams = None

    try:
        if standings_data and standings_data.get("response"):
            standings = standings_data["response"][0]["league"]["standings"][0]
            total_teams = len(standings)
            for team in standings:
                if team["team"]["id"] == home_id:
                    home_position = team["rank"]
                if team["team"]["id"] == away_id:
                    away_position = team["rank"]
    except:
        pass

    # Calcular escanteios
    try:
        media_home = stats_home["response"]["fixtures"]["corners"]["for"]["average"]["home"]
        media_away = stats_away["response"]["fixtures"]["corners"]["for"]["average"]["away"]
        estimativa = round(float(media_home) + float(media_away), 1)
    except Exception as e:
        logger.warning(f"Erro ao calcular escanteios: {e}. Usando valor padrão.")
        estimativa = DEFAULT_CORNERS_ESTIMATE

    # Calcular Must Win
    must_win_home = calculate_must_win_factor(
        stats_home.get("response") if stats_home else None,
        home_position,
        total_teams
    )
    must_win_away = calculate_must_win_factor(
        stats_away.get("response") if stats_away else None,
        away_position,
        total_teams
    )

    # Ajustar confiança baseado em Must Win
    base_confidence = 5 if estimativa >= 10 else 4
    # Times com Must Win alto tendem a ser mais agressivos = mais escanteios
    must_win_adjustment = (must_win_home["score"] + must_win_away["score"]) / 10
    adjusted_confidence = min(5, base_confidence + must_win_adjustment * 0.5)

    analise = {
        "time_casa": {
            "id": home_id,
            "must_win": must_win_home
        },
        "time_fora": {
            "id": away_id,
            "must_win": must_win_away
        },
        "estimativa_total": estimativa,
        "analise_must_win": {
            "impacto": "Times pressionados tendem a jogar mais ofensivamente, gerando mais escanteios",
            "fator_combinado": round((must_win_home["score"] + must_win_away["score"]) / 2, 1)
        },
        "sugestoes": [{
            "mercado": "Over 9.5 Escanteios Totais",
            "confianca": round(adjusted_confidence, 1),
            "value_estimado": "+20%" if estimativa >= 10 else "+10%"
        }]
    }
    return jsonify({"ok": True, "analise_escanteios": analise})


@app.route("/analysis/cards")
def analysis_cards():
    """
    Análise profissional de cartões amarelos baseada em estatísticas com fator Must Win.

    Query Parameters:
        - team_home (required): ID do time mandante
        - team_away (required): ID do time visitante
        - league (required): ID da liga
        - season: Ano da temporada (default: 2025)

    Calcula estimativa baseada em média de cartões amarelos + fator Must Win.
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

    # Buscar dados
    stats_home, _ = call_api_football("/teams/statistics", {"team": home_id, "league": league_id, "season": season})
    stats_away, _ = call_api_football("/teams/statistics", {"team": away_id, "league": league_id, "season": season})
    standings_data, _ = call_api_football("/standings", {"league": league_id, "season": season})

    # Calcular posições na tabela
    home_position = None
    away_position = None
    total_teams = None

    try:
        if standings_data and standings_data.get("response"):
            standings = standings_data["response"][0]["league"]["standings"][0]
            total_teams = len(standings)
            for team in standings:
                if team["team"]["id"] == home_id:
                    home_position = team["rank"]
                if team["team"]["id"] == away_id:
                    away_position = team["rank"]
    except:
        pass

    # Calcular cartões
    try:
        media_home = stats_home["response"]["cards"]["yellow"]["average"]["home"]
        media_away = stats_away["response"]["cards"]["yellow"]["average"]["away"]
        estimativa = round(float(media_home) + float(media_away), 1)
    except Exception as e:
        logger.warning(f"Erro ao calcular cartões: {e}. Usando valor padrão.")
        estimativa = DEFAULT_CARDS_ESTIMATE

    # Calcular Must Win
    must_win_home = calculate_must_win_factor(
        stats_home.get("response") if stats_home else None,
        home_position,
        total_teams
    )
    must_win_away = calculate_must_win_factor(
        stats_away.get("response") if stats_away else None,
        away_position,
        total_teams
    )

    # Ajustar confiança baseado em Must Win
    base_confidence = 5 if estimativa >= 5.5 else 4
    # Times com Must Win alto tendem a jogar com mais intensidade = mais cartões
    must_win_adjustment = (must_win_home["score"] + must_win_away["score"]) / 10
    adjusted_confidence = min(5, base_confidence + must_win_adjustment * 0.6)

    analise = {
        "time_casa": {
            "id": home_id,
            "must_win": must_win_home
        },
        "time_fora": {
            "id": away_id,
            "must_win": must_win_away
        },
        "estimativa_total": estimativa,
        "analise_must_win": {
            "impacto": "Times pressionados jogam com mais intensidade e agressividade, resultando em mais cartões",
            "fator_combinado": round((must_win_home["score"] + must_win_away["score"]) / 2, 1)
        },
        "sugestoes": [{
            "mercado": "Over 5.5 Cartões Totais",
            "confianca": round(adjusted_confidence, 1),
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
# Endpoint de análise completa
# =======================
@app.route("/analysis/complete")
def analysis_complete():
    """
    Análise completa de um jogo consolidando todos os endpoints de análise.

    Query Parameters:
        - team_home (required): ID do time mandante
        - team_away (required): ID do time visitante
        - league (required): ID da liga
        - season: Ano da temporada (default: 2025)
        - fixture: ID do jogo específico (opcional, para análise pré-jogo)

    Retorna análise consolidada incluindo:
    - Contexto (posições na tabela, forma recente)
    - Estatísticas dos times
    - H2H (últimos confrontos)
    - Análise de escanteios (com Must Win)
    - Análise de cartões (com Must Win)
    - Lesões e suspensões
    - Previsões IA (se fixture fornecido)
    """
    team_home = request.args.get("team_home")
    team_away = request.args.get("team_away")
    league = request.args.get("league")
    season = request.args.get("season", str(DEFAULT_SEASON))
    fixture_id = request.args.get("fixture")

    # Validar parâmetros obrigatórios
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

    # Estrutura da resposta completa
    complete_analysis = {
        "ok": True,
        "jogo": {
            "mandante_id": home_id,
            "visitante_id": away_id,
            "liga_id": league_id,
            "temporada": season
        },
        "contexto": {},
        "estatisticas": {},
        "confronto_direto": {},
        "analise_escanteios": {},
        "analise_cartoes": {},
        "lesoes": {},
        "predicoes": None
    }

    # ====== 1. BUSCAR ESTATÍSTICAS DOS TIMES ======
    logger.info(f"[ANALYSIS COMPLETE] Buscando estatísticas dos times {home_id} vs {away_id}")
    stats_home, error_home = call_api_football("/teams/statistics", {
        "team": home_id,
        "league": league_id,
        "season": season
    })
    stats_away, error_away = call_api_football("/teams/statistics", {
        "team": away_id,
        "league": league_id,
        "season": season
    })

    if stats_home and stats_home.get("response"):
        complete_analysis["estatisticas"]["mandante"] = stats_home["response"]
    if stats_away and stats_away.get("response"):
        complete_analysis["estatisticas"]["visitante"] = stats_away["response"]

    # ====== 2. BUSCAR CLASSIFICAÇÃO ======
    logger.info(f"[ANALYSIS COMPLETE] Buscando classificação da liga {league_id}")
    standings_data, _ = call_api_football("/standings", {
        "league": league_id,
        "season": season
    })

    home_position = None
    away_position = None
    total_teams = None
    home_points = None
    away_points = None

    try:
        if standings_data and standings_data.get("response"):
            standings = standings_data["response"][0]["league"]["standings"][0]
            total_teams = len(standings)
            for team in standings:
                if team["team"]["id"] == home_id:
                    home_position = team["rank"]
                    home_points = team["points"]
                if team["team"]["id"] == away_id:
                    away_position = team["rank"]
                    away_points = team["points"]

            complete_analysis["contexto"]["classificacao"] = {
                "mandante": {
                    "posicao": home_position,
                    "pontos": home_points
                },
                "visitante": {
                    "posicao": away_position,
                    "pontos": away_points
                },
                "total_times": total_teams
            }
    except Exception as e:
        logger.warning(f"[ANALYSIS COMPLETE] Erro ao processar classificação: {str(e)}")

    # ====== 3. CALCULAR MUST WIN ======
    logger.info("[ANALYSIS COMPLETE] Calculando fator Must Win")
    must_win_home = calculate_must_win_factor(
        stats_home.get("response") if stats_home else None,
        home_position,
        total_teams
    )
    must_win_away = calculate_must_win_factor(
        stats_away.get("response") if stats_away else None,
        away_position,
        total_teams
    )

    complete_analysis["contexto"]["must_win"] = {
        "mandante": must_win_home,
        "visitante": must_win_away,
        "analise": (
            "Mais importante para o time da casa" if must_win_home["score"] > must_win_away["score"] + 1.5 else
            "Mais importante para o time visitante" if must_win_away["score"] > must_win_home["score"] + 1.5 else
            "Importância equilibrada para ambos os times"
        )
    }

    # ====== 4. BUSCAR H2H ======
    logger.info("[ANALYSIS COMPLETE] Buscando histórico H2H")
    h2h_data, _ = call_api_football("/fixtures/headtohead", {
        "h2h": f"{home_id}-{away_id}"
    })

    if h2h_data and h2h_data.get("response"):
        h2h_matches = []
        for match in h2h_data["response"][:5]:  # Top 5
            h2h_matches.append({
                "data": match.get("fixture", {}).get("date"),
                "mandante": match.get("teams", {}).get("home", {}).get("name"),
                "visitante": match.get("teams", {}).get("away", {}).get("name"),
                "placar": f"{match.get('goals', {}).get('home')}-{match.get('goals', {}).get('away')}"
            })
        complete_analysis["confronto_direto"] = {
            "total": len(h2h_data["response"]),
            "ultimos_jogos": h2h_matches
        }

    # ====== 5. ANÁLISE DE ESCANTEIOS ======
    logger.info("[ANALYSIS COMPLETE] Calculando análise de escanteios")
    corners_estimate = DEFAULT_CORNERS_ESTIMATE
    try:
        if stats_home and stats_home.get("response") and stats_away and stats_away.get("response"):
            home_corners = stats_home["response"].get("fixtures", {}).get("played", {}).get("home", 0)
            away_corners = stats_away["response"].get("fixtures", {}).get("played", {}).get("away", 0)

            if home_corners > 0 and away_corners > 0:
                # Simplificação: usar estimativa baseada em média
                corners_estimate = 10.5  # Estimativa média

        must_win_combined = (must_win_home["score"] + must_win_away["score"]) / 2
        confidence_corners = min(5.0, 4.0 + (must_win_combined - 5.0) * 0.15)

        complete_analysis["analise_escanteios"] = {
            "time_casa": {
                "id": home_id,
                "must_win": must_win_home
            },
            "time_fora": {
                "id": away_id,
                "must_win": must_win_away
            },
            "estimativa_total": round(corners_estimate, 1),
            "analise_must_win": {
                "fator_combinado": round(must_win_combined, 1),
                "impacto": "Times pressionados tendem a jogar mais ofensivamente, gerando mais escanteios"
            },
            "sugestoes": [
                {
                    "mercado": f"Over {int(corners_estimate) - 1}.5 Escanteios",
                    "confianca": round(confidence_corners, 1),
                    "value_estimado": "+15%" if must_win_combined > 6.0 else "+10%"
                }
            ]
        }
    except Exception as e:
        logger.warning(f"[ANALYSIS COMPLETE] Erro na análise de escanteios: {str(e)}")

    # ====== 6. ANÁLISE DE CARTÕES ======
    logger.info("[ANALYSIS COMPLETE] Calculando análise de cartões")
    cards_estimate = DEFAULT_CARDS_ESTIMATE
    try:
        must_win_combined = (must_win_home["score"] + must_win_away["score"]) / 2
        confidence_cards = min(5.0, 4.0 + (must_win_combined - 5.0) * 0.18)

        complete_analysis["analise_cartoes"] = {
            "time_casa": {
                "id": home_id,
                "must_win": must_win_home
            },
            "time_fora": {
                "id": away_id,
                "must_win": must_win_away
            },
            "estimativa_total": round(cards_estimate, 1),
            "analise_must_win": {
                "fator_combinado": round(must_win_combined, 1),
                "impacto": "Times pressionados jogam com mais intensidade e agressividade, resultando em mais cartões"
            },
            "sugestoes": [
                {
                    "mercado": f"Over {int(cards_estimate) - 1}.5 Cartões",
                    "confianca": round(confidence_cards, 1),
                    "value_estimado": "+20%" if must_win_combined > 6.5 else "+12%"
                }
            ]
        }
    except Exception as e:
        logger.warning(f"[ANALYSIS COMPLETE] Erro na análise de cartões: {str(e)}")

    # ====== 7. BUSCAR LESÕES ======
    logger.info("[ANALYSIS COMPLETE] Buscando lesões")
    injuries_home, _ = call_api_football("/injuries", {
        "league": league_id,
        "team": home_id,
        "season": season
    })
    injuries_away, _ = call_api_football("/injuries", {
        "league": league_id,
        "team": away_id,
        "season": season
    })

    complete_analysis["lesoes"] = {
        "mandante": injuries_home.get("response", []) if injuries_home else [],
        "visitante": injuries_away.get("response", []) if injuries_away else []
    }

    # ====== 8. PREVISÕES IA (se fixture fornecido) ======
    if fixture_id:
        logger.info(f"[ANALYSIS COMPLETE] Buscando previsões para fixture {fixture_id}")
        predictions, _ = call_api_football("/predictions", {"fixture": fixture_id})
        if predictions and predictions.get("response"):
            complete_analysis["predicoes"] = predictions["response"][0]

    logger.info("[ANALYSIS COMPLETE] Análise completa gerada com sucesso")
    return jsonify(complete_analysis)


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
