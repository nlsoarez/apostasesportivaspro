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
import threading

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
API_VERSION = "6.0"
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

# Sportradar API
API_KEY = os.getenv("API_KEY")
SPORTRADAR_BASE_URL = os.getenv("SPORTRADAR_BASE_URL", "https://api.sportradar.com/soccer/trial/v4/en")
API_TIMEOUT = float(os.getenv("API_TIMEOUT", "15"))
API_MAX_RETRIES = int(os.getenv("API_MAX_RETRIES", "3"))
API_RETRY_DELAY = float(os.getenv("API_RETRY_DELAY", "1.2"))  # Sportradar trial: 1 req/sec
NEWS_API_KEY = os.getenv("NEWS_API_KEY", "")

# Rate limiter para Sportradar trial (1 req/sec)
_last_request_time = 0.0
_rate_limit_lock = threading.Lock()

def _rate_limit():
    """Garante no mínimo 1 segundo entre requisições (Sportradar trial: QPS=1)."""
    global _last_request_time
    with _rate_limit_lock:
        now = time.time()
        elapsed = now - _last_request_time
        if elapsed < 1.1:
            time.sleep(1.1 - elapsed)
        _last_request_time = time.time()

# Validação crítica de API_KEY
if not API_KEY:
    logger.error("ERRO CRITICO: API_KEY nao configurada!")
    logger.error("Configure a variavel de ambiente API_KEY com sua chave Sportradar.")

# =======================
# Competições suportadas (Sportradar URNs)
# =======================
SUPPORTED_COMPETITIONS = {
    # Brasil
    "sr:competition:325": "Brasileirao Serie A",
    "sr:competition:390": "Brasileirao Serie B",
    "sr:competition:531": "Copa do Brasil",
    "sr:competition:621": "Campeonato Carioca",
    "sr:competition:624": "Campeonato Paulista",
    # Europa
    "sr:competition:17":  "Premier League",
    "sr:competition:8":   "La Liga",
    "sr:competition:23":  "Serie A (Italia)",
    "sr:competition:35":  "Bundesliga",
    "sr:competition:34":  "Ligue 1",
    "sr:competition:238": "Primeira Liga",
    "sr:competition:37":  "Eredivisie",
    # Internacional / Clubes
    "sr:competition:7":   "UEFA Champions League",
    "sr:competition:679": "UEFA Europa League",
    "sr:competition:929": "UEFA Conference League",
    "sr:competition:384": "Copa Libertadores",
    "sr:competition:480": "Copa Sul-Americana",
    # Américas
    "sr:competition:242": "MLS",
    "sr:competition:316": "Liga MX",
    # Seleções
    "sr:competition:1":   "Copa do Mundo FIFA",
    "sr:competition:9":   "Eurocopa",
    "sr:competition:133": "Copa America"
}

# =======================
# Funções utilitárias
# =======================
def call_sportradar(path, params=None, max_retries=None):
    """
    Chama a Sportradar Soccer API v4 com rate limiting e retry automático.

    Args:
        path (str): Caminho do endpoint (ex: /schedules/2025-03-01/summaries.json)
        params (dict): Parâmetros adicionais da query string (sem api_key)
        max_retries (int): Número máximo de tentativas

    Returns:
        tuple: (data, error) onde data é o JSON de resposta ou None em caso de erro
    """
    if not API_KEY:
        return None, "API_KEY nao configurada. Configure sua chave Sportradar."

    if max_retries is None:
        max_retries = API_MAX_RETRIES

    url = f"{SPORTRADAR_BASE_URL}{path}"
    query_params = {"api_key": API_KEY}
    if params:
        query_params.update(params)

    last_error = None

    for attempt in range(max_retries):
        try:
            _rate_limit()
            timeout = API_TIMEOUT + (attempt * 2)
            response = requests.get(url, params=query_params, timeout=timeout)

            if response.status_code == 200:
                return response.json(), None

            elif response.status_code == 401:
                body = response.text[:300] if response.text else "(sem corpo)"
                logger.error(f"[Sportradar] Chave invalida (401) -> {path} | body: {body}")
                return None, f"API_KEY invalida ou expirada (401). Verifique sua chave no portal Sportradar. Detalhe: {body}"

            elif response.status_code == 403:
                body = response.text[:300] if response.text else "(sem corpo)"
                logger.error(f"[Sportradar] Sem permissao (403) -> {path} | body: {body}")
                return None, f"Sem permissao para este endpoint (403): {path}. Detalhe Sportradar: {body}"

            elif response.status_code == 404:
                logger.warning(f"[Sportradar] Nao encontrado (404) -> {path}")
                return None, f"Recurso nao encontrado: {path}"

            elif response.status_code in [429, 500, 502, 503, 504]:
                last_error = f"HTTP {response.status_code}"
                logger.warning(f"[Sportradar Retry {attempt+1}/{max_retries}] {last_error} -> {path}")
                if attempt < max_retries - 1:
                    delay = API_RETRY_DELAY * (2 ** attempt)
                    time.sleep(delay)
                    continue
            else:
                logger.error(f"[Sportradar] HTTP {response.status_code} -> {path}")
                return None, f"Erro HTTP {response.status_code}"

        except requests.exceptions.Timeout:
            last_error = "Timeout na requisicao"
            logger.warning(f"[Sportradar Timeout {attempt+1}/{max_retries}] {path}")
            if attempt < max_retries - 1:
                time.sleep(API_RETRY_DELAY * (2 ** attempt))
                continue

        except requests.exceptions.ConnectionError:
            last_error = "Erro de conexao"
            logger.warning(f"[Sportradar Connection Error {attempt+1}/{max_retries}] {path}")
            if attempt < max_retries - 1:
                time.sleep(API_RETRY_DELAY * (2 ** attempt))
                continue

        except Exception as e:
            last_error = str(e)
            logger.error(f"[Sportradar Exception] {last_error}")
            return None, last_error

    logger.error(f"[Sportradar] Todas as {max_retries} tentativas falharam para {path}")
    return None, f"Falha apos {max_retries} tentativas: {last_error}"


def error_response(msg, status=400):
    return jsonify({"ok": False, "error": msg}), status


def validate_numeric_param(value, param_name, min_val=None, max_val=None, required=True):
    if value is None:
        if required:
            return None, f"Parametro '{param_name}' e obrigatorio"
        return None, None
    try:
        num_value = float(value)
    except (ValueError, TypeError):
        return None, f"Parametro '{param_name}' deve ser numerico"
    if min_val is not None and num_value < min_val:
        return None, f"Parametro '{param_name}' deve ser >= {min_val}"
    if max_val is not None and num_value > max_val:
        return None, f"Parametro '{param_name}' deve ser <= {max_val}"
    return num_value, None


def validate_urn_param(value, param_name, prefix="sr:", required=True):
    """Valida um parâmetro URN do Sportradar (ex: sr:competition:325)."""
    if not value:
        if required:
            return None, f"Parametro '{param_name}' e obrigatorio (ex: sr:competition:325)"
        return None, None
    if not str(value).startswith(prefix):
        return None, f"Parametro '{param_name}' deve ser um URN Sportradar valido (ex: sr:competition:325)"
    return str(value), None


def calculate_must_win_factor(form_str=None, position=None, total_teams=None):
    """
    Calcula o fator 'Must Win' para um time baseado em sua situação.

    Returns:
        dict com score (0-10), nivel e fatores
    """
    must_win_score = 5.0
    factors = []

    if position and total_teams:
        relegation_zone = total_teams - 3
        classification_zone = 6
        if position >= relegation_zone:
            must_win_score += 3.0
            factors.append({
                "fator": "Zona de Rebaixamento",
                "impacto": "CRITICO",
                "descricao": f"Time na {position}a posicao (zona de rebaixamento)"
            })
        elif position >= (relegation_zone - 3):
            must_win_score += 2.0
            factors.append({
                "fator": "Proximo a Zona de Rebaixamento",
                "impacto": "ALTO",
                "descricao": f"Time proximo da zona perigosa ({position}a posicao)"
            })
        elif position <= classification_zone:
            must_win_score += 1.5
            factors.append({
                "fator": "Briga por Classificacao",
                "impacto": "MODERADO",
                "descricao": f"Time brigando por vaga em competicoes ({position}a posicao)"
            })

    if form_str:
        try:
            recent_losses = form_str[-5:].count("L")
            recent_draws = form_str[-5:].count("D")
            recent_wins = form_str[-5:].count("W")
            if recent_losses >= 3:
                must_win_score += 2.0
                factors.append({
                    "fator": "Sequencia Negativa",
                    "impacto": "ALTO",
                    "descricao": f"{recent_losses} derrotas nos ultimos 5 jogos"
                })
            elif recent_losses >= 2 and recent_draws >= 2:
                must_win_score += 1.5
                factors.append({
                    "fator": "Momento Instavel",
                    "impacto": "MODERADO",
                    "descricao": "Sequencia inconsistente de resultados"
                })
            elif recent_wins >= 4:
                must_win_score -= 1.0
                factors.append({
                    "fator": "Boa Sequencia",
                    "impacto": "BAIXO",
                    "descricao": f"{recent_wins} vitorias nos ultimos 5 jogos"
                })
        except Exception:
            pass

    must_win_score = max(0, min(10, must_win_score))
    return {
        "score": round(must_win_score, 1),
        "nivel": (
            "CRITICO" if must_win_score >= 8 else
            "ALTO" if must_win_score >= 6.5 else
            "MODERADO" if must_win_score >= 5 else
            "BAIXO"
        ),
        "fatores": factors,
        "recomendacao": (
            "Time sob EXTREMA pressao por resultado. Analise de motivacao e crucial." if must_win_score >= 8 else
            "Time precisa pontuar. Fator motivacional significativo." if must_win_score >= 6.5 else
            "Jogo importante, mas sem pressao extrema." if must_win_score >= 5 else
            "Time em situacao confortavel."
        )
    }


def _get_current_season_urn(competition_urn):
    """
    Busca a URN da temporada atual (mais recente) para uma competição.
    Retorna (season_urn, error).
    """
    comp_id = competition_urn.replace(":", "%3A") if "%" not in competition_urn else competition_urn
    data, error = call_sportradar(f"/competitions/{competition_urn}/seasons.json")
    if error:
        return None, error
    seasons = data.get("seasons", [])
    if not seasons:
        return None, "Nenhuma temporada encontrada para esta competicao"
    # Retorna a mais recente (maior ano)
    current_year = datetime.now().year
    best = None
    for s in seasons:
        year = s.get("year", "")
        if str(current_year) in str(year):
            best = s
            break
    if not best:
        best = seasons[0]  # fallback para a primeira
    return best.get("id"), None


def _get_team_form(competitor_urn):
    """
    Calcula string de forma (W/D/L) dos últimos 5 jogos de um time.
    Retorna (form_str, error) ex: ("WWDLW", None)
    Consome 1 chamada à API Sportradar.
    """
    data, error = call_sportradar(f"/competitors/{competitor_urn}/summaries.json")
    if error:
        return None, error

    form = []
    for summary in data.get("summaries", []):
        if len(form) >= 5:
            break
        status_obj = summary.get("sport_event_status", {})
        if status_obj.get("status") not in ("closed", "ended"):
            continue

        competitors = summary.get("sport_event", {}).get("competitors", [])
        qualifier = None
        for c in competitors:
            if c.get("id") == competitor_urn:
                qualifier = c.get("qualifier")
                break

        home_score = int(status_obj.get("home_score") or 0)
        away_score = int(status_obj.get("away_score") or 0)

        if qualifier == "home":
            team_score, opp_score = home_score, away_score
        elif qualifier == "away":
            team_score, opp_score = away_score, home_score
        else:
            continue

        if team_score > opp_score:
            form.append("W")
        elif team_score == opp_score:
            form.append("D")
        else:
            form.append("L")

    return "".join(form) if form else None, None


def _parse_status_sportradar(status_str):
    """Converte status Sportradar para abreviação conhecida."""
    mapping = {
        "not_started": "NS",
        "live": "LIVE",
        "1st_half": "1H",
        "halftime": "HT",
        "2nd_half": "2H",
        "overtime": "ET",
        "penalties": "PEN",
        "ended": "FT",
        "closed": "FT",
        "abandoned": "ABD",
        "delayed": "DELAY",
        "postponed": "PST",
        "cancelled": "CANC",
        "interrupted": "INT",
        "suspended": "SUSP",
    }
    return mapping.get(status_str, status_str.upper() if status_str else "?")


# =======================
# Endpoints básicos
# =======================
@app.route("/")
def home():
    return jsonify({
        "ok": True,
        "name": "Apostas Esportivas Pro API",
        "version": API_VERSION,
        "provider": "Sportradar Soccer API v4",
        "description": "API profissional integrada com Sportradar para analises esportivas avancadas.",
        "documentation": "/openapi.json",
        "endpoints": {
            "base": ["/health", "/competitions", "/fixtures", "/standings", "/players/topscorers"],
            "avancados": ["/fixtures/headtohead", "/predictions", "/fixtures/live"],
            "ao_vivo": ["/fixtures/live/analysis", "/fixtures/live/minute-by-minute"],
            "profissionais": ["/analysis/corners", "/analysis/cards", "/analysis/value",
                              "/news/context", "/analysis/complete"],
            "utilidades": ["/seasons"]
        },
        "nota_ids": (
            "Esta API usa URNs do Sportradar. "
            "Use /competitions para listar competicoes disponiveis. "
            "Exemplo de competition_id: sr:competition:325 (Brasileirao Serie A). "
            "Use /seasons?competition=sr:competition:325 para obter season_id."
        ),
        "rate_limit": "Trial: 1 req/seg, 1000 req/dia"
    })


@app.route("/health")
def health():
    status = {
        "ok": True,
        "message": "API operacional",
        "version": API_VERSION,
        "provider": "Sportradar Soccer API v4",
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

    if API_KEY:
        try:
            # Testa conectividade chamando endpoint de competições
            data, error = call_sportradar("/competitions.json")
            if error:
                status["sportradar_status"] = "error"
                status["sportradar_error"] = error
                if "invalida" in error or "401" in error:
                    status["sportradar_status"] = "invalid_key"
            else:
                competitions = data.get("competitions", [])
                status["sportradar_status"] = "connected"
                status["sportradar_competitions_count"] = len(competitions)
        except Exception as e:
            status["sportradar_status"] = "unknown"
            logger.warning(f"Health check Sportradar falhou: {e}")
    else:
        status["sportradar_status"] = "not_configured"
        status["warning"] = "API_KEY nao configurada"

    return jsonify(status)


@app.route("/debug/test-api")
def debug_test_api():
    """
    Testa quais endpoints Sportradar estão acessíveis com a API key atual.
    Útil para diagnosticar problemas de permissão 403.
    """
    if not API_KEY:
        return jsonify({"ok": False, "error": "API_KEY nao configurada"}), 500

    today = datetime.now().strftime("%Y-%m-%d")
    test_endpoints = [
        "/competitions.json",
        f"/schedules/{today}/schedule.json",
        f"/schedules/{today}/summaries.json",
        "/schedules/live/summaries.json",
    ]

    results = {}
    base_url = SPORTRADAR_BASE_URL

    for ep in test_endpoints:
        try:
            _rate_limit()
            url = f"{base_url}{ep}"
            resp = requests.get(url, params={"api_key": API_KEY}, timeout=10)
            body_preview = resp.text[:200] if resp.text else ""
            results[ep] = {
                "status_code": resp.status_code,
                "ok": resp.status_code == 200,
                "body_preview": body_preview
            }
        except Exception as e:
            results[ep] = {"status_code": None, "ok": False, "error": str(e)}

    any_ok = any(v["ok"] for v in results.values())
    return jsonify({
        "ok": any_ok,
        "api_key_configured": bool(API_KEY),
        "api_key_prefix": API_KEY[:8] + "..." if API_KEY else None,
        "base_url": base_url,
        "endpoints_tested": results
    })


@app.route("/openapi.json")
def openapi_json():
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        yaml_path = os.path.join(base_dir, "openapi.yaml")
        if not os.path.exists(yaml_path):
            yaml_path = "openapi.yaml"
        if os.path.exists(yaml_path):
            with open(yaml_path, "r", encoding="utf-8") as f:
                openapi_yaml = yaml.safe_load(f)
            return jsonify(openapi_yaml)
        else:
            return jsonify({
                "openapi": "3.1.0",
                "info": {
                    "title": "Apostas Esportivas Pro API",
                    "version": API_VERSION,
                    "description": "API profissional integrada com Sportradar Soccer API v4."
                },
                "paths": {}
            })
    except Exception as e:
        return error_response(f"Erro ao carregar schema: {str(e)}", 500)


@app.route("/competitions")
def competitions():
    """
    Lista competições disponíveis.
    Retorna as competições conhecidas + proxy para /competitions.json do Sportradar.

    Query Parameters:
        - live: Se 'true', busca as competições ao vivo no momento
    """
    # Lista estática conhecida
    known = [
        {"id": cid, "name": name}
        for cid, name in sorted(SUPPORTED_COMPETITIONS.items(), key=lambda x: x[1])
    ]

    return jsonify({
        "ok": True,
        "total": len(known),
        "competitions": known,
        "categories": {
            "brasil": [
                "sr:competition:325", "sr:competition:390",
                "sr:competition:531", "sr:competition:621", "sr:competition:624"
            ],
            "europa": [
                "sr:competition:17", "sr:competition:8", "sr:competition:23",
                "sr:competition:35", "sr:competition:34", "sr:competition:238",
                "sr:competition:37"
            ],
            "internacional_clubes": [
                "sr:competition:7", "sr:competition:679", "sr:competition:929",
                "sr:competition:384", "sr:competition:480"
            ],
            "americas": ["sr:competition:242", "sr:competition:316"],
            "selecoes": ["sr:competition:1", "sr:competition:9", "sr:competition:133"]
        },
        "nota": "Use o 'id' como parametro 'competition' nos outros endpoints"
    })


# Manter /leagues como alias de /competitions para compatibilidade
@app.route("/leagues")
def leagues():
    return competitions()


@app.route("/seasons")
def seasons():
    """
    Lista temporadas disponíveis para uma competição.

    Query Parameters:
        - competition (required): URN da competição (ex: sr:competition:325)
    """
    competition = request.args.get("competition")
    if not competition:
        return error_response("Parametro 'competition' e obrigatorio (ex: sr:competition:325)")

    data, error = call_sportradar(f"/competitions/{competition}/seasons.json")
    if error:
        return error_response(error, 500)

    seasons_list = []
    for s in data.get("seasons", []):
        seasons_list.append({
            "id": s.get("id"),
            "name": s.get("name"),
            "year": s.get("year"),
            "start_date": s.get("start_date"),
            "end_date": s.get("end_date"),
            "competition_id": s.get("competition_id")
        })

    return jsonify({
        "ok": True,
        "competition": competition,
        "total": len(seasons_list),
        "seasons": seasons_list,
        "nota": "Use o 'id' da temporada como parametro 'season' nos outros endpoints"
    })


# =======================
# Endpoints principais
# =======================
@app.route("/fixtures", methods=["GET"])
def fixtures():
    """
    Lista jogos por data e/ou competição.

    Query Parameters:
        - date (required): Data no formato YYYY-MM-DD
        - competition: URN da competição para filtrar (ex: sr:competition:325)

    Retorna os jogos do dia com status e placar (se finalizado).
    """
    date = request.args.get("date")
    competition_filter = request.args.get("competition")

    if not date:
        date = datetime.now().strftime("%Y-%m-%d")

    data, error = call_sportradar(f"/schedules/{date}/summaries.json")
    if error:
        return error_response(error, 500)

    summaries = data.get("summaries", [])
    jogos = []

    for summary in summaries:
        sport_event = summary.get("sport_event", {})
        status_obj = summary.get("sport_event_status", {})

        # Filtrar por competição se solicitado
        ctx = sport_event.get("sport_event_context", {})
        comp = ctx.get("competition", {})
        comp_id = comp.get("id", "")
        if competition_filter and comp_id != competition_filter:
            continue

        competitors = sport_event.get("competitors", [])
        home_name = away_name = None
        home_id = away_id = None
        home_score = away_score = None

        for c in competitors:
            q = c.get("qualifier", "")
            if q == "home":
                home_name = c.get("name")
                home_id = c.get("id")
            elif q == "away":
                away_name = c.get("name")
                away_id = c.get("id")

        status_str = status_obj.get("status", "")
        home_score = status_obj.get("home_score")
        away_score = status_obj.get("away_score")
        match_time = status_obj.get("clock", {}).get("match_time") if status_str == "live" else None

        jogos.append({
            "id": sport_event.get("id"),
            "data": sport_event.get("scheduled"),
            "status": _parse_status_sportradar(status_str),
            "minuto": match_time,
            "competicao": comp.get("name"),
            "competicao_id": comp_id,
            "mandante": home_name,
            "mandante_id": home_id,
            "visitante": away_name,
            "visitante_id": away_id,
            "placar": f"{home_score}x{away_score}" if home_score is not None else None
        })

    return jsonify({
        "ok": True,
        "date": date,
        "total": len(jogos),
        "jogos": jogos
    })


@app.route("/standings")
def standings():
    """
    Retorna a classificação de uma competição.

    Query Parameters:
        - competition (required): URN da competição (ex: sr:competition:325)
        - season: URN da temporada (ex: sr:season:106479). Se omitido, usa a atual.
    """
    competition = request.args.get("competition")
    season_urn = request.args.get("season")

    if not competition:
        return error_response("Parametro 'competition' e obrigatorio (ex: sr:competition:325)")

    # Auto-detectar temporada atual se não fornecida
    if not season_urn:
        season_urn, error = _get_current_season_urn(competition)
        if error:
            return error_response(f"Nao foi possivel detectar a temporada atual: {error}", 500)

    data, error = call_sportradar(
        f"/competitions/{competition}/seasons/{season_urn}/standings.json"
    )
    if error:
        return error_response(error, 500)

    standings_raw = data.get("standings", [])
    result = []

    for standing in standings_raw:
        if standing.get("type") != "total":
            continue
        for group in standing.get("groups", []):
            for entry in group.get("standings", []):
                team = entry.get("team", {})
                result.append({
                    "posicao": entry.get("rank"),
                    "time": team.get("name"),
                    "time_id": team.get("id"),
                    "jogos": entry.get("played", 0),
                    "vitorias": entry.get("win", 0),
                    "empates": entry.get("draw", 0),
                    "derrotas": entry.get("loss", 0),
                    "gols_pro": entry.get("goals_scored", 0),
                    "gols_contra": entry.get("goals_conceded", 0),
                    "saldo": entry.get("goals_scored", 0) - entry.get("goals_conceded", 0),
                    "pontos": entry.get("points", 0)
                })

    result.sort(key=lambda x: x.get("posicao") or 999)
    return jsonify({
        "ok": True,
        "competition": competition,
        "season": season_urn,
        "total": len(result),
        "classificacao": result
    })


@app.route("/teams/statistics")
def team_statistics():
    """
    Retorna perfil e estatísticas de um time (competitor).

    Query Parameters:
        - team (required): URN do time (ex: sr:competitor:1234)
        - competition: URN da competição para contexto
        - season: URN da temporada
    """
    team = request.args.get("team")
    competition = request.args.get("competition")
    season_urn = request.args.get("season")

    if not team:
        return error_response("Parametro 'team' e obrigatorio (ex: sr:competitor:1234)")

    # Buscar perfil do competitor
    data, error = call_sportradar(f"/competitors/{team}/profile.json")
    if error:
        return error_response(error, 500)

    competitor = data.get("competitor", {})
    players = data.get("players", [])
    categories = data.get("categories", [])

    # Se tiver season, busca sumários da temporada
    summaries_data = None
    if season_urn and competition:
        summaries_data, _ = call_sportradar(
            f"/competitions/{competition}/seasons/{season_urn}/competitor_statistics.json",
            params={"competitor": team}
        )

    return jsonify({
        "ok": True,
        "team": {
            "id": competitor.get("id"),
            "name": competitor.get("name"),
            "short_name": competitor.get("short_name"),
            "abbreviation": competitor.get("abbreviation"),
            "country": competitor.get("country"),
            "country_code": competitor.get("country_code"),
            "gender": competitor.get("gender"),
            "type": competitor.get("type")
        },
        "jogadores": [
            {
                "id": p.get("id"),
                "name": p.get("name"),
                "date_of_birth": p.get("date_of_birth"),
                "nationality": p.get("nationality"),
                "height": p.get("height"),
                "weight": p.get("weight"),
                "jersey_number": p.get("jersey_number"),
                "position": p.get("type")
            }
            for p in players[:30]  # Top 30 jogadores
        ],
        "estatisticas_temporada": summaries_data
    })


@app.route("/players/topscorers")
def top_scorers():
    """
    Retorna artilheiros de uma competição/temporada.

    Query Parameters:
        - competition (required): URN da competição (ex: sr:competition:325)
        - season: URN da temporada. Se omitido, usa a atual.
    """
    competition = request.args.get("competition")
    season_urn = request.args.get("season")

    if not competition:
        return error_response("Parametro 'competition' e obrigatorio (ex: sr:competition:325)")

    if not season_urn:
        season_urn, error = _get_current_season_urn(competition)
        if error:
            return error_response(f"Nao foi possivel detectar a temporada: {error}", 500)

    data, error = call_sportradar(
        f"/competitions/{competition}/seasons/{season_urn}/top_scorers.json"
    )
    if error:
        return error_response(error, 500)

    top_scorers_raw = data.get("top_scorers", {})
    artilheiros = []

    for entry in top_scorers_raw.get("competitors", []):
        comp = entry.get("competitor", {})
        for player_entry in entry.get("players", []):
            player = player_entry.get("player", {})
            stats = player_entry.get("statistics", {})
            artilheiros.append({
                "jogador": player.get("name"),
                "jogador_id": player.get("id"),
                "time": comp.get("name"),
                "time_id": comp.get("id"),
                "gols": stats.get("goals_scored", 0),
                "assistencias": stats.get("assists", 0),
                "jogos": stats.get("appearances", 0),
                "amarelos": stats.get("yellow_cards", 0),
                "vermelhos": stats.get("red_cards", 0)
            })

    artilheiros.sort(key=lambda x: x.get("gols", 0), reverse=True)
    return jsonify({
        "ok": True,
        "competition": competition,
        "season": season_urn,
        "total": len(artilheiros),
        "artilheiros": artilheiros
    })


# =======================
# Endpoints avançados
# =======================
@app.route("/fixtures/headtohead")
def head_to_head():
    """
    Retorna histórico de confrontos diretos (H2H) entre dois times.

    Query Parameters:
        - team1 (required): URN do time 1 (ex: sr:competitor:1234)
        - team2 (required): URN do time 2 (ex: sr:competitor:5678)
    """
    team1 = request.args.get("team1")
    team2 = request.args.get("team2")

    if not team1 or not team2:
        return error_response(
            "Parametros 'team1' e 'team2' sao obrigatorios. "
            "Exemplo: team1=sr:competitor:1234&team2=sr:competitor:5678"
        )

    data, error = call_sportradar(
        f"/competitors/{team1}/versus/{team2}/summaries.json"
    )
    if error:
        return error_response(error, 500)

    last_meetings = data.get("last_meetings", {})
    results_raw = last_meetings.get("results", [])

    resultados = []
    for match in results_raw[:MAX_H2H_RESULTS]:
        sport_event = match.get("sport_event", {})
        status_obj = match.get("sport_event_status", {})
        competitors = sport_event.get("competitors", [])

        home_name = away_name = None
        for c in competitors:
            if c.get("qualifier") == "home":
                home_name = c.get("name")
            elif c.get("qualifier") == "away":
                away_name = c.get("name")

        home_score = status_obj.get("home_score", 0)
        away_score = status_obj.get("away_score", 0)

        resultados.append({
            "id": sport_event.get("id"),
            "data": sport_event.get("scheduled"),
            "mandante": home_name,
            "visitante": away_name,
            "placar": f"{home_score}x{away_score}",
            "status": _parse_status_sportradar(status_obj.get("status", ""))
        })

    next_meetings = data.get("next_meetings", {})
    proximos = []
    for match in next_meetings.get("results", [])[:5]:
        sport_event = match.get("sport_event", {})
        competitors = sport_event.get("competitors", [])
        home_name = away_name = None
        for c in competitors:
            if c.get("qualifier") == "home":
                home_name = c.get("name")
            elif c.get("qualifier") == "away":
                away_name = c.get("name")
        proximos.append({
            "id": sport_event.get("id"),
            "data": sport_event.get("scheduled"),
            "mandante": home_name,
            "visitante": away_name
        })

    return jsonify({
        "ok": True,
        "team1": team1,
        "team2": team2,
        "total_historico": len(resultados),
        "resultados": resultados,
        "proximos": proximos
    })


@app.route("/predictions")
def predictions():
    """
    Retorna probabilidades de resultado de um jogo (sport event).

    Query Parameters:
        - fixture (required): URN do jogo (ex: sr:sport_event:12345)
    """
    fixture = request.args.get("fixture")
    if not fixture:
        return error_response("Parametro 'fixture' e obrigatorio (ex: sr:sport_event:12345)")

    data, error = call_sportradar(f"/sport_events/{fixture}/probabilities.json")
    if error:
        return error_response(error, 500)

    sport_event = data.get("sport_event", {})
    probabilities = data.get("probabilities", [])

    result = []
    for market in probabilities:
        market_name = market.get("market")
        outcomes = []
        for outcome in market.get("outcomes", []):
            outcomes.append({
                "resultado": outcome.get("outcome"),
                "probabilidade": round(outcome.get("probability", 0) * 100, 1),
                "probabilidade_decimal": outcome.get("probability")
            })
        result.append({
            "mercado": market_name,
            "resultados": outcomes
        })

    competitors = sport_event.get("competitors", [])
    home_name = away_name = None
    for c in competitors:
        if c.get("qualifier") == "home":
            home_name = c.get("name")
        elif c.get("qualifier") == "away":
            away_name = c.get("name")

    return jsonify({
        "ok": True,
        "jogo": {
            "id": sport_event.get("id"),
            "data": sport_event.get("scheduled"),
            "mandante": home_name,
            "visitante": away_name
        },
        "predicoes": result
    })


@app.route("/fixtures/live")
def live_fixtures():
    """
    Lista jogos ao vivo no momento.
    Retorna os jogos que estão acontecendo agora com placar e minuto.
    """
    data, error = call_sportradar("/schedules/live/summaries.json")
    if error:
        return error_response(error, 500)

    summaries = data.get("summaries", [])
    partidas = []

    for summary in summaries[:MAX_LIVE_FIXTURES]:
        sport_event = summary.get("sport_event", {})
        status_obj = summary.get("sport_event_status", {})

        competitors = sport_event.get("competitors", [])
        home_name = away_name = None
        for c in competitors:
            if c.get("qualifier") == "home":
                home_name = c.get("name")
            elif c.get("qualifier") == "away":
                away_name = c.get("name")

        ctx = sport_event.get("sport_event_context", {})
        comp = ctx.get("competition", {})
        clock = status_obj.get("clock", {})

        home_score = status_obj.get("home_score", 0)
        away_score = status_obj.get("away_score", 0)

        partidas.append({
            "id": sport_event.get("id"),
            "status": _parse_status_sportradar(status_obj.get("status", "")),
            "match_status": status_obj.get("match_status"),
            "minuto": clock.get("match_time"),
            "competicao": comp.get("name"),
            "competicao_id": comp.get("id"),
            "mandante": home_name,
            "visitante": away_name,
            "placar": f"{home_score}x{away_score}"
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
    Análise profissional de um jogo ao vivo com fator Must Win.

    Query Parameters:
        - fixture (required): URN do jogo (ex: sr:sport_event:12345)

    Retorna análise completa incluindo:
    - Placar e minuto atuais
    - Fator Must Win (baseado em tabela se disponível)
    - Estatísticas da partida (via timeline)
    - Sugestões de apostas ao vivo
    """
    fixture_id = request.args.get("fixture")
    if not fixture_id:
        return error_response("Parametro 'fixture' e obrigatorio (ex: sr:sport_event:12345)")

    # Buscar sumário do jogo ao vivo
    data, error = call_sportradar(f"/sport_events/{fixture_id}/summary.json")
    if error:
        return error_response(error, 500)

    sport_event = data.get("sport_event", {})
    status_obj = data.get("sport_event_status", {})
    statistics = data.get("statistics", {})

    competitors = sport_event.get("competitors", [])
    home_name = home_id = None
    away_name = away_id = None
    for c in competitors:
        if c.get("qualifier") == "home":
            home_name = c.get("name")
            home_id = c.get("id")
        elif c.get("qualifier") == "away":
            away_name = c.get("name")
            away_id = c.get("id")

    clock = status_obj.get("clock", {})
    elapsed = int(clock.get("match_time", 0) or 0)
    match_status = status_obj.get("match_status", "")
    home_score = status_obj.get("home_score", 0)
    away_score = status_obj.get("away_score", 0)

    # Análise de momento do jogo
    momento = "Inicio de jogo"
    if elapsed > 75:
        momento = "Final de jogo - Pressao maxima"
    elif elapsed > 60:
        momento = "Reta final - Momento decisivo"
    elif elapsed > 45:
        momento = "Segundo tempo"
    elif elapsed > 30:
        momento = "Final do primeiro tempo"

    # Must Win com forma recente
    form_home, _ = _get_team_form(home_id) if home_id else (None, None)
    form_away, _ = _get_team_form(away_id) if away_id else (None, None)
    must_win_home = calculate_must_win_factor(form_home)
    must_win_away = calculate_must_win_factor(form_away)

    # Estatísticas ao vivo por time
    live_stats = {"mandante": {}, "visitante": {}}
    totals = statistics.get("totals", {})
    if totals:
        competitors_stats = totals.get("competitors", [])
        for cs in competitors_stats:
            cs_id = cs.get("id")
            stats_dict = cs.get("statistics", {})
            if cs_id == home_id:
                live_stats["mandante"] = stats_dict
            elif cs_id == away_id:
                live_stats["visitante"] = stats_dict

    # Sugestões baseadas no contexto ao vivo
    sugestoes = []
    total_goals = (home_score or 0) + (away_score or 0)
    if elapsed > 60 and total_goals == 0:
        sugestoes.append({
            "tipo": "Gols",
            "mercado": "Ambas marcam - NAO",
            "justificativa": f"Jogo sem gols aos {elapsed}' - defesas solidas",
            "confianca": 4
        })
    elif total_goals >= 2 and elapsed < 60:
        sugestoes.append({
            "tipo": "Gols",
            "mercado": "Over 2.5 ou 3.5 gols",
            "justificativa": f"{total_goals} gols em apenas {elapsed}' - jogo aberto",
            "confianca": 4
        })

    # Escanteios
    try:
        h_corners = live_stats["mandante"].get("corner_kicks", 0) or 0
        a_corners = live_stats["visitante"].get("corner_kicks", 0) or 0
        total_corners = int(h_corners) + int(a_corners)
        if elapsed > 0:
            proj = round(total_corners / elapsed * 90, 1)
            sugestoes.append({
                "tipo": "Escanteios",
                "mercado": f"Projecao: {proj} escanteios no jogo",
                "justificativa": f"{total_corners} escanteios em {elapsed}' ({round(total_corners/elapsed, 2)}/min)",
                "confianca": 4 if elapsed > 30 else 3
            })
    except Exception:
        pass

    return jsonify({
        "ok": True,
        "jogo": {
            "id": fixture_id,
            "status": _parse_status_sportradar(status_obj.get("status", "")),
            "match_status": match_status,
            "minuto": elapsed,
            "momento_jogo": momento,
            "mandante": home_name,
            "visitante": away_name,
            "placar": {
                "atual": f"{home_score}x{away_score}",
                "halftime": None
            }
        },
        "estatisticas_ao_vivo": live_stats,
        "must_win": {
            "mandante": must_win_home,
            "visitante": must_win_away,
            "analise": "Importancia equilibrada para ambos (dados de tabela nao disponíveis ao vivo)"
        },
        "sugestoes_ao_vivo": sugestoes,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    })


@app.route("/fixtures/live/minute-by-minute")
def minute_by_minute_analysis():
    """
    Análise minuto a minuto de um jogo via timeline de eventos.

    Query Parameters:
        - fixture (required): URN do jogo (ex: sr:sport_event:12345)

    Retorna:
    - Timeline completa de eventos (gols, cartões, substituições)
    - Análise de cada período (0-15, 16-30, 31-45, etc.)
    - Momentos-chave identificados
    """
    fixture_id = request.args.get("fixture")
    if not fixture_id:
        return error_response("Parametro 'fixture' e obrigatorio (ex: sr:sport_event:12345)")

    data, error = call_sportradar(f"/sport_events/{fixture_id}/timeline.json")
    if error:
        return error_response(error, 500)

    sport_event = data.get("sport_event", {})
    status_obj = data.get("sport_event_status", {})
    timeline_raw = data.get("timeline", [])

    competitors = sport_event.get("competitors", [])
    home_name = away_name = None
    for c in competitors:
        if c.get("qualifier") == "home":
            home_name = c.get("name")
        elif c.get("qualifier") == "away":
            away_name = c.get("name")

    # Processar eventos
    timeline = []
    goals_timeline = []
    cards_timeline = []
    substitutions = []

    for event in timeline_raw:
        minute = event.get("match_time", 0) or 0
        event_type = event.get("type", "")
        competitor = event.get("competitor", "")
        player = event.get("player", {})
        player_name = player.get("name", "Desconhecido") if player else "Desconhecido"

        # Mapear team name
        team_name = home_name if competitor == "home" else (away_name if competitor == "away" else competitor)

        event_obj = {
            "minuto": minute,
            "minuto_display": f"{minute}'",
            "tipo": event_type,
            "time": team_name,
            "jogador": player_name,
            "descricao": event.get("description", "")
        }

        if event_type in ("score_change",):
            event_obj["placar"] = {
                "mandante": event.get("home_score"),
                "visitante": event.get("away_score")
            }
            goals_timeline.append(event_obj)
        elif event_type in ("yellow_card", "red_card", "yellow_red_card"):
            cards_timeline.append(event_obj)
        elif event_type in ("substitution",):
            substitutions.append(event_obj)

        timeline.append(event_obj)

    # Análise por períodos
    periods = {
        "0-15": {"gols": 0, "cartoes": 0, "eventos": []},
        "16-30": {"gols": 0, "cartoes": 0, "eventos": []},
        "31-45": {"gols": 0, "cartoes": 0, "eventos": []},
        "46-60": {"gols": 0, "cartoes": 0, "eventos": []},
        "61-75": {"gols": 0, "cartoes": 0, "eventos": []},
        "76-90+": {"gols": 0, "cartoes": 0, "eventos": []}
    }

    def get_period(m):
        if m <= 15: return "0-15"
        if m <= 30: return "16-30"
        if m <= 45: return "31-45"
        if m <= 60: return "46-60"
        if m <= 75: return "61-75"
        return "76-90+"

    for event in timeline:
        m = event.get("minuto", 0)
        p = get_period(m)
        if event["tipo"] == "score_change":
            periods[p]["gols"] += 1
        elif event["tipo"] in ("yellow_card", "red_card", "yellow_red_card"):
            periods[p]["cartoes"] += 1
        periods[p]["eventos"].append(event)

    # Momentos-chave
    momentos_chave = []
    if periods["0-15"]["gols"] > 0:
        momentos_chave.append({
            "periodo": "0-15",
            "descricao": f"Inicio eletrico com {periods['0-15']['gols']} gol(s)",
            "impacto": "ALTO"
        })

    periodo_mais_movimentado = max(periods.items(), key=lambda x: len(x[1]["eventos"]))
    if len(periodo_mais_movimentado[1]["eventos"]) >= 5:
        momentos_chave.append({
            "periodo": periodo_mais_movimentado[0],
            "descricao": f"Periodo mais agitado com {len(periodo_mais_movimentado[1]['eventos'])} eventos",
            "impacto": "MODERADO"
        })

    return jsonify({
        "ok": True,
        "jogo": {
            "id": fixture_id,
            "mandante": home_name,
            "visitante": away_name,
            "status": _parse_status_sportradar(status_obj.get("status", "")),
            "placar": {
                "mandante": status_obj.get("home_score"),
                "visitante": status_obj.get("away_score")
            }
        },
        "timeline_completa": sorted(timeline, key=lambda x: x["minuto"]),
        "analise_por_periodos": periods,
        "momentos_chave": momentos_chave,
        "resumo": {
            "total_eventos": len(timeline),
            "total_gols": len(goals_timeline),
            "total_cartoes": len(cards_timeline),
            "total_substituicoes": len(substitutions)
        },
        "timestamp": datetime.utcnow().isoformat() + "Z"
    })


@app.route("/injuries")
def injuries():
    """
    Jogadores ausentes (lesionados/suspensos) de uma competição/temporada.

    Query Parameters:
        - competition (required): URN da competição (ex: sr:competition:325)
        - team (optional): URN do time para filtrar (ex: sr:competitor:1234)
        - season (optional): URN da temporada (auto-detecta se omitido)
    """
    competition = request.args.get("competition")
    team_filter = request.args.get("team")
    season_urn = request.args.get("season")

    if not competition:
        return error_response(
            "Parametro 'competition' e obrigatorio (ex: sr:competition:325). "
            "Use /competitions para listar os IDs disponíveis."
        )

    if not season_urn:
        season_urn, error = _get_current_season_urn(competition)
        if error:
            return error_response(f"Nao foi possivel detectar a temporada: {error}", 500)

    data, error = call_sportradar(
        f"/competitions/{competition}/seasons/{season_urn}/missing_players.json"
    )
    if error:
        return error_response(error, 500)

    missing = data.get("missing_players", {})
    competitors_raw = missing.get("competitors", [])

    lesoes = []
    for comp_entry in competitors_raw:
        comp = comp_entry.get("competitor", {})
        comp_id = comp.get("id")
        comp_name = comp.get("name")

        # Filtrar por time se solicitado
        if team_filter and comp_id != team_filter:
            continue

        for player_entry in comp_entry.get("players", []):
            player = player_entry.get("player", {})
            lesoes.append({
                "time": comp_name,
                "time_id": comp_id,
                "jogador": player.get("name"),
                "jogador_id": player.get("id"),
                "tipo": player_entry.get("type"),
                "lesionado": player_entry.get("injured", False),
                "desde": player_entry.get("started_at"),
                "retorno_previsto": player_entry.get("return_date")
            })

    return jsonify({
        "ok": True,
        "competition": competition,
        "season": season_urn,
        "team_filter": team_filter,
        "total": len(lesoes),
        "lesoes": lesoes
    })


@app.route("/odds")
def odds():
    """
    Odds de um jogo.
    Nota: Odds não estão incluídas no pacote Soccer Base do Sportradar.
    Use /predictions para probabilidades calculadas pela Sportradar.

    Query Parameters:
        - fixture (required): URN do jogo (ex: sr:sport_event:12345)
    """
    fixture = request.args.get("fixture")
    if not fixture:
        return error_response("Parametro 'fixture' e obrigatorio (ex: sr:sport_event:12345)")

    return jsonify({
        "ok": False,
        "error": (
            "Odds de casas de apostas nao estao incluidas no plano Sportradar Soccer Base. "
            "Use /predictions para obter probabilidades calculadas pela Sportradar."
        ),
        "alternativa": f"/predictions?fixture={fixture}"
    }), 503


# =======================
# Endpoints profissionais
# =======================
@app.route("/analysis/corners")
def analysis_corners():
    """
    Análise de escanteios com fator Must Win.

    Query Parameters:
        - competition (required): URN da competição
        - season (required): URN da temporada
        - team_home (required): URN do time mandante
        - team_away (required): URN do time visitante

    Baseia-se em informações da tabela (standings) para calcular Must Win.
    """
    competition = request.args.get("competition")
    season_urn = request.args.get("season")
    team_home = request.args.get("team_home")
    team_away = request.args.get("team_away")

    if not (competition and team_home and team_away):
        return error_response("Parametros obrigatorios: competition, team_home, team_away")

    # Auto-detectar temporada
    if not season_urn:
        season_urn, error = _get_current_season_urn(competition)
        if error:
            return error_response(f"Nao foi possivel detectar a temporada: {error}", 500)

    # Buscar standings para calcular posições
    standings_data, _ = call_sportradar(
        f"/competitions/{competition}/seasons/{season_urn}/standings.json"
    )

    home_position = away_position = total_teams = None
    home_points = away_points = 0

    try:
        if standings_data:
            for standing in standings_data.get("standings", []):
                if standing.get("type") != "total":
                    continue
                for group in standing.get("groups", []):
                    entries = group.get("standings", [])
                    total_teams = len(entries)
                    for entry in entries:
                        t = entry.get("team", {})
                        if t.get("id") == team_home:
                            home_position = entry.get("rank")
                            home_points = entry.get("points", 0)
                        if t.get("id") == team_away:
                            away_position = entry.get("rank")
                            away_points = entry.get("points", 0)
    except Exception as e:
        logger.warning(f"Erro ao processar standings para corners: {e}")

    form_home, _ = _get_team_form(team_home)
    form_away, _ = _get_team_form(team_away)
    must_win_home = calculate_must_win_factor(form_home, home_position, total_teams)
    must_win_away = calculate_must_win_factor(form_away, away_position, total_teams)

    estimativa = DEFAULT_CORNERS_ESTIMATE
    must_win_combined = (must_win_home["score"] + must_win_away["score"]) / 2
    base_confidence = 4.0
    adjusted_confidence = min(5.0, base_confidence + (must_win_combined - 5.0) * 0.15)

    return jsonify({
        "ok": True,
        "analise_escanteios": {
            "time_casa": {"id": team_home, "posicao": home_position, "pontos": home_points, "must_win": must_win_home},
            "time_fora": {"id": team_away, "posicao": away_position, "pontos": away_points, "must_win": must_win_away},
            "estimativa_total": estimativa,
            "analise_must_win": {
                "impacto": "Times pressionados tendem a jogar mais ofensivamente, gerando mais escanteios",
                "fator_combinado": round(must_win_combined, 1)
            },
            "sugestoes": [{
                "mercado": "Over 9.5 Escanteios Totais",
                "confianca": round(adjusted_confidence, 1),
                "value_estimado": "+20%" if estimativa >= 10 else "+10%"
            }],
            "nota": "Estimativa baseada em posicao na tabela (Must Win). Para maior precisao, use estatisticas de escanteios do time via /teams/statistics."
        }
    })


@app.route("/analysis/cards")
def analysis_cards():
    """
    Análise de cartões com fator Must Win.

    Query Parameters:
        - competition (required): URN da competição
        - season: URN da temporada (auto-detecta se omitido)
        - team_home (required): URN do time mandante
        - team_away (required): URN do time visitante
    """
    competition = request.args.get("competition")
    season_urn = request.args.get("season")
    team_home = request.args.get("team_home")
    team_away = request.args.get("team_away")

    if not (competition and team_home and team_away):
        return error_response("Parametros obrigatorios: competition, team_home, team_away")

    if not season_urn:
        season_urn, error = _get_current_season_urn(competition)
        if error:
            return error_response(f"Nao foi possivel detectar a temporada: {error}", 500)

    standings_data, _ = call_sportradar(
        f"/competitions/{competition}/seasons/{season_urn}/standings.json"
    )

    home_position = away_position = total_teams = None

    try:
        if standings_data:
            for standing in standings_data.get("standings", []):
                if standing.get("type") != "total":
                    continue
                for group in standing.get("groups", []):
                    entries = group.get("standings", [])
                    total_teams = len(entries)
                    for entry in entries:
                        t = entry.get("team", {})
                        if t.get("id") == team_home:
                            home_position = entry.get("rank")
                        if t.get("id") == team_away:
                            away_position = entry.get("rank")
    except Exception as e:
        logger.warning(f"Erro ao processar standings para cards: {e}")

    form_home, _ = _get_team_form(team_home)
    form_away, _ = _get_team_form(team_away)
    must_win_home = calculate_must_win_factor(form_home, home_position, total_teams)
    must_win_away = calculate_must_win_factor(form_away, away_position, total_teams)

    estimativa = DEFAULT_CARDS_ESTIMATE
    must_win_combined = (must_win_home["score"] + must_win_away["score"]) / 2
    base_confidence = 4.0
    adjusted_confidence = min(5.0, base_confidence + (must_win_combined - 5.0) * 0.2)

    return jsonify({
        "ok": True,
        "analise_cartoes": {
            "time_casa": {"id": team_home, "posicao": home_position, "must_win": must_win_home},
            "time_fora": {"id": team_away, "posicao": away_position, "must_win": must_win_away},
            "estimativa_total": estimativa,
            "analise_must_win": {
                "impacto": "Times pressionados jogam com mais intensidade, resultando em mais cartoes",
                "fator_combinado": round(must_win_combined, 1)
            },
            "sugestoes": [{
                "mercado": "Over 5.5 Cartoes Totais",
                "confianca": round(adjusted_confidence, 1),
                "value_estimado": "+25%" if estimativa >= 5.5 else "+10%"
            }]
        }
    })


@app.route("/analysis/value")
def analysis_value():
    """
    Calcula Value Bet usando a fórmula: (probabilidade × odd) - 1

    Query Parameters:
        - odd (required): Odd da casa de apostas (1.01 - 100.0)
        - probability (required): Probabilidade estimada (0.01 - 1.0)
    """
    odd_str = request.args.get("odd")
    prob_str = request.args.get("probability")

    odd, error = validate_numeric_param(odd_str, "odd", min_val=MIN_ODD_VALUE, max_val=MAX_ODD_VALUE)
    if error:
        return error_response(f"{error}. Exemplo: odd=2.50")

    prob, error = validate_numeric_param(
        prob_str, "probability", min_val=MIN_PROBABILITY, max_val=MAX_PROBABILITY
    )
    if error:
        return error_response(f"{error}. Exemplo: probability=0.50 (50%)")

    value = round((prob * odd) - 1, 3)
    return jsonify({
        "ok": True,
        "value": value,
        "interpretation": "Value Bet" if value > 0 else "Sem Value",
        "recommendation": "Apostar" if value > 0.05 else "Evitar",
        "formula": f"({prob} x {odd}) - 1 = {value}"
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
    """
    team = request.args.get("team")
    league = request.args.get("league")
    days_str = request.args.get("days", str(DEFAULT_NEWS_DAYS))

    if not team:
        return error_response("Parametro 'team' e obrigatorio. Exemplo: team=Flamengo")

    try:
        days = int(days_str)
    except (ValueError, TypeError):
        return error_response("Parametro 'days' deve ser um inteiro")

    if days < 1 or days > MAX_NEWS_DAYS:
        return error_response(f"Parametro 'days' deve estar entre 1 e {MAX_NEWS_DAYS}")

    if not NEWS_API_KEY:
        return error_response("NEWS_API_KEY nao configurada", 503)

    query = f"{team} {league or ''} futebol lesao suspensao demitido tecnico site:ge.globo.com OR site:espn.com.br"
    url = "https://newsapi.org/v2/everything"
    params = {
        "q": query,
        "language": "pt",
        "sortBy": "publishedAt",
        "pageSize": 5,
        "from": (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d"),
    }

    try:
        response = requests.get(url, headers={"Authorization": NEWS_API_KEY}, params=params, timeout=10)
        if response.status_code != 200:
            return error_response(f"Erro na API de noticias: HTTP {response.status_code}", 500)

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
        return error_response(f"Erro ao buscar noticias: {str(e)}", 500)


# =======================
# Análise completa
# =======================
@app.route("/analysis/complete")
def analysis_complete():
    """
    Análise completa de um jogo consolidando standings, H2H e Must Win.

    Query Parameters:
        - competition (required): URN da competição (ex: sr:competition:325)
        - team_home (required): URN do time mandante (ex: sr:competitor:1234)
        - team_away (required): URN do time visitante (ex: sr:competitor:5678)
        - season: URN da temporada (auto-detecta se omitido)
        - fixture: URN do jogo para probabilidades (ex: sr:sport_event:12345)

    Retorna análise consolidada com:
    - Classificação dos times
    - Fator Must Win
    - H2H (últimos confrontos)
    - Probabilidades (se fixture fornecido)
    - Análise de escanteios e cartões (baseada em Must Win)
    """
    competition = request.args.get("competition")
    team_home = request.args.get("team_home")
    team_away = request.args.get("team_away")
    season_urn = request.args.get("season")
    fixture_id = request.args.get("fixture")

    if not (competition and team_home and team_away):
        return error_response("Parametros obrigatorios: competition, team_home, team_away")

    complete_analysis = {
        "ok": True,
        "jogo": {
            "mandante_id": team_home,
            "visitante_id": team_away,
            "competicao_id": competition,
            "temporada": season_urn
        },
        "contexto": {},
        "confronto_direto": {},
        "probabilidades": None,
        "analise_escanteios": {},
        "analise_cartoes": {}
    }

    # 1. Auto-detectar temporada
    if not season_urn:
        logger.info("[ANALYSIS COMPLETE] Detectando temporada atual...")
        season_urn, error = _get_current_season_urn(competition)
        if error:
            logger.warning(f"[ANALYSIS COMPLETE] Falha ao detectar temporada: {error}")
        else:
            complete_analysis["jogo"]["temporada"] = season_urn

    # 2. Buscar standings
    if season_urn:
        logger.info(f"[ANALYSIS COMPLETE] Buscando classificacao de {competition}")
        standings_data, _ = call_sportradar(
            f"/competitions/{competition}/seasons/{season_urn}/standings.json"
        )

        home_position = away_position = total_teams = None
        home_points = away_points = 0
        home_name = away_name = None

        try:
            if standings_data:
                for standing in standings_data.get("standings", []):
                    if standing.get("type") != "total":
                        continue
                    for group in standing.get("groups", []):
                        entries = group.get("standings", [])
                        total_teams = len(entries)
                        for entry in entries:
                            t = entry.get("team", {})
                            if t.get("id") == team_home:
                                home_position = entry.get("rank")
                                home_points = entry.get("points", 0)
                                home_name = t.get("name")
                            if t.get("id") == team_away:
                                away_position = entry.get("rank")
                                away_points = entry.get("points", 0)
                                away_name = t.get("name")
        except Exception as e:
            logger.warning(f"[ANALYSIS COMPLETE] Erro ao processar standings: {e}")

        if home_name:
            complete_analysis["jogo"]["mandante_nome"] = home_name
        if away_name:
            complete_analysis["jogo"]["visitante_nome"] = away_name

        complete_analysis["contexto"]["classificacao"] = {
            "mandante": {"posicao": home_position, "pontos": home_points},
            "visitante": {"posicao": away_position, "pontos": away_points},
            "total_times": total_teams
        }

        # 3. Must Win com forma recente
        logger.info("[ANALYSIS COMPLETE] Buscando forma recente dos times")
        form_home, _ = _get_team_form(team_home)
        form_away, _ = _get_team_form(team_away)
        must_win_home = calculate_must_win_factor(form_home, home_position, total_teams)
        must_win_away = calculate_must_win_factor(form_away, away_position, total_teams)
        complete_analysis["contexto"]["must_win"] = {
            "mandante": must_win_home,
            "visitante": must_win_away,
            "analise": (
                "Mais importante para o time da casa" if must_win_home["score"] > must_win_away["score"] + 1.5 else
                "Mais importante para o time visitante" if must_win_away["score"] > must_win_home["score"] + 1.5 else
                "Importancia equilibrada para ambos os times"
            )
        }

        # Análise de escanteios e cartões
        must_win_combined = (must_win_home["score"] + must_win_away["score"]) / 2
        complete_analysis["analise_escanteios"] = {
            "estimativa_total": DEFAULT_CORNERS_ESTIMATE,
            "fator_must_win": round(must_win_combined, 1),
            "sugestao": "Over 9.5 Escanteios Totais" if must_win_combined >= 5 else "Indefinido"
        }
        complete_analysis["analise_cartoes"] = {
            "estimativa_total": DEFAULT_CARDS_ESTIMATE,
            "fator_must_win": round(must_win_combined, 1),
            "sugestao": "Over 5.5 Cartoes Totais" if must_win_combined >= 5 else "Indefinido"
        }
    else:
        form_home, _ = _get_team_form(team_home)
        form_away, _ = _get_team_form(team_away)
        must_win_home = calculate_must_win_factor(form_home)
        must_win_away = calculate_must_win_factor(form_away)

    # 4. H2H
    logger.info("[ANALYSIS COMPLETE] Buscando historico H2H")
    h2h_data, _ = call_sportradar(
        f"/competitors/{team_home}/versus/{team_away}/summaries.json"
    )
    if h2h_data:
        last = h2h_data.get("last_meetings", {}).get("results", [])
        h2h_matches = []
        for match in last[:5]:
            se = match.get("sport_event", {})
            so = match.get("sport_event_status", {})
            comps = se.get("competitors", [])
            hn = an = None
            for c in comps:
                if c.get("qualifier") == "home": hn = c.get("name")
                if c.get("qualifier") == "away": an = c.get("name")
            h2h_matches.append({
                "data": se.get("scheduled"),
                "mandante": hn,
                "visitante": an,
                "placar": f"{so.get('home_score', 0)}-{so.get('away_score', 0)}"
            })
        complete_analysis["confronto_direto"] = {
            "total": len(last),
            "ultimos_jogos": h2h_matches
        }

    # 5. Probabilidades (se fixture fornecido)
    if fixture_id:
        logger.info(f"[ANALYSIS COMPLETE] Buscando probabilidades do jogo {fixture_id}")
        prob_data, _ = call_sportradar(f"/sport_events/{fixture_id}/probabilities.json")
        if prob_data:
            probs = prob_data.get("probabilities", [])
            prob_3way = next((p for p in probs if p.get("market") == "3way"), None)
            if prob_3way:
                outcomes = {o["outcome"]: round(o["probability"] * 100, 1) for o in prob_3way.get("outcomes", [])}
                complete_analysis["probabilidades"] = {
                    "mercado": "3way",
                    "vitoria_mandante": outcomes.get("home_team_winner"),
                    "empate": outcomes.get("draw"),
                    "vitoria_visitante": outcomes.get("away_team_winner")
                }

    return jsonify(complete_analysis)


# =======================
# Inicialização
# =======================
if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    debug = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    logger.info(f"Iniciando Apostas Esportivas Pro API v{API_VERSION} na porta {port}")
    logger.info(f"Provider: Sportradar Soccer API v4")
    app.run(host="0.0.0.0", port=port, debug=debug)
