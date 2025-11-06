"""
🎯 API APOSTAS ESPORTIVAS PRO
Versão 3.0 - Melhorada e Robusta

Melhorias implementadas:
- ✅ Retry automático em falhas
- ✅ Cache Redis (opcional)
- ✅ Logs estruturados
- ✅ Validação de parâmetros
- ✅ Rate limiting
- ✅ CORS configurado
- ✅ Tratamento de erros robusto
- ✅ Sem API keys hardcoded
"""

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import requests
from datetime import datetime, timedelta
import json
import time
import logging
from functools import wraps
from typing import Optional, Dict, Any, Tuple

# ============================================================
# 🔧 CONFIGURAÇÃO
# ============================================================

app = Flask(__name__)

# CORS configurado corretamente
CORS(app, resources={
    r"/*": {
        "origins": ["https://chat.openai.com", "https://chatgpt.com"],
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})

# Configuração de Logs
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================
# 🔐 VARIÁVEIS DE AMBIENTE
# ============================================================

API_KEY = os.getenv("API_KEY")
if not API_KEY:
    logger.error("⚠️  API_KEY não configurada! Configure a variável de ambiente.")
    
API_HOST = os.getenv("API_HOST", "v3.football.api-sports.io")
PORT = int(os.getenv("PORT", 8080))
FLASK_ENV = os.getenv("FLASK_ENV", "production")

# Redis (opcional)
REDIS_URL = os.getenv("REDIS_URL")
redis_client = None

try:
    if REDIS_URL:
        import redis
        redis_client = redis.from_url(REDIS_URL, decode_responses=True)
        logger.info("✅ Redis conectado")
except Exception as e:
    logger.warning(f"⚠️  Redis não disponível: {e}")

# ============================================================
# 🛡️ DECORADORES E UTILITÁRIOS
# ============================================================

def rate_limit(max_calls=100, period=3600):
    """Decorator para rate limiting (100 calls/hora por padrão)"""
    def decorator(f):
        calls = {}
        
        @wraps(f)
        def wrapper(*args, **kwargs):
            now = time.time()
            client_id = request.remote_addr
            
            # Limpar chamadas antigas
            if client_id in calls:
                calls[client_id] = [t for t in calls[client_id] if now - t < period]
            else:
                calls[client_id] = []
            
            # Verificar limite
            if len(calls[client_id]) >= max_calls:
                return jsonify({
                    "ok": False,
                    "error": "Rate limit excedido. Tente novamente mais tarde.",
                    "limite": f"{max_calls} requisições por hora"
                }), 429
            
            # Registrar chamada
            calls[client_id].append(now)
            return f(*args, **kwargs)
        
        return wrapper
    return decorator


def validate_params(required_params):
    """Decorator para validar parâmetros obrigatórios"""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            missing = []
            for param in required_params:
                if not request.args.get(param):
                    missing.append(param)
            
            if missing:
                return jsonify({
                    "ok": False,
                    "error": f"Parâmetros obrigatórios faltando: {', '.join(missing)}",
                    "parametros_necessarios": required_params
                }), 400
            
            return f(*args, **kwargs)
        return wrapper
    return decorator


def cache_response(ttl=300):
    """Decorator para cache de respostas (5 minutos por padrão)"""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if not redis_client:
                return f(*args, **kwargs)
            
            # Gerar chave de cache
            cache_key = f"cache:{f.__name__}:{request.full_path}"
            
            # Tentar obter do cache
            try:
                cached = redis_client.get(cache_key)
                if cached:
                    logger.info(f"📦 Cache hit: {cache_key}")
                    return jsonify(json.loads(cached))
            except Exception as e:
                logger.warning(f"Erro ao ler cache: {e}")
            
            # Executar função e cachear resultado
            response = f(*args, **kwargs)
            
            try:
                if isinstance(response, tuple):
                    data, status = response
                else:
                    data = response
                    status = 200
                
                if status == 200 and data:
                    redis_client.setex(
                        cache_key,
                        ttl,
                        json.dumps(data.get_json() if hasattr(data, 'get_json') else data)
                    )
                    logger.info(f"💾 Cached: {cache_key}")
            except Exception as e:
                logger.warning(f"Erro ao salvar cache: {e}")
            
            return response
        return wrapper
    return decorator

# ============================================================
# 🔧 FUNÇÃO PARA CHAMAR API COM RETRY
# ============================================================

def call_api_football(
    endpoint: str, 
    params: Dict[str, Any],
    max_retries: int = 3,
    retry_delay: float = 1.0
) -> Tuple[Optional[Dict], Optional[str]]:
    """
    Chama a API-Football com retry automático
    
    Args:
        endpoint: Endpoint da API (ex: /fixtures)
        params: Parâmetros da requisição
        max_retries: Número máximo de tentativas
        retry_delay: Delay entre tentativas (em segundos)
    
    Returns:
        Tupla (dados, erro)
    """
    
    if not API_KEY:
        return None, "API_KEY não configurada"
    
    url = f"https://{API_HOST}{endpoint}"
    headers = {"x-apisports-key": API_KEY}
    
    for attempt in range(max_retries):
        try:
            logger.info(f"📡 Chamando: {endpoint} (tentativa {attempt + 1}/{max_retries})")
            logger.debug(f"   Params: {params}")
            
            response = requests.get(
                url, 
                headers=headers, 
                params=params, 
                timeout=10
            )
            
            logger.info(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                
                # Verificar se há erros na resposta
                if data.get("errors") and len(data["errors"]) > 0:
                    error_msg = str(data["errors"])
                    logger.error(f"❌ Erro da API: {error_msg}")
                    return None, error_msg
                
                logger.info(f"✅ Sucesso: {len(data.get('response', []))} resultados")
                return data, None
            
            elif response.status_code == 429:
                # Rate limit - aguardar mais tempo
                wait_time = retry_delay * (attempt + 1) * 2
                logger.warning(f"⏳ Rate limit atingido. Aguardando {wait_time}s...")
                time.sleep(wait_time)
                continue
            
            else:
                error_msg = f"Erro {response.status_code}: {response.text[:200]}"
                logger.error(f"❌ {error_msg}")
                
                if attempt < max_retries - 1:
                    time.sleep(retry_delay * (attempt + 1))
                    continue
                
                return None, error_msg
        
        except requests.exceptions.Timeout:
            logger.error(f"⏱️  Timeout na tentativa {attempt + 1}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay * (attempt + 1))
                continue
            return None, "Timeout na requisição"
        
        except Exception as e:
            error_msg = f"Erro na requisição: {str(e)}"
            logger.error(f"❌ {error_msg}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay * (attempt + 1))
                continue
            return None, error_msg
    
    return None, "Número máximo de tentativas excedido"

# ============================================================
# 📅 ENDPOINT: HEALTH CHECK
# ============================================================

@app.route("/health", methods=["GET"])
def health():
    """Endpoint de health check"""
    
    # Testar conexão com API
    api_status = "unknown"
    try:
        response = requests.get(
            f"https://{API_HOST}/status",
            headers={"x-apisports-key": API_KEY} if API_KEY else {},
            timeout=5
        )
        api_status = "connected" if response.status_code == 200 else "error"
    except:
        api_status = "timeout"
    
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "api_key_configured": bool(API_KEY),
        "api_host": API_HOST,
        "api_connection": api_status,
        "redis_available": redis_client is not None,
        "version": "3.0.0",
        "environment": FLASK_ENV
    })

# ============================================================
# 📅 ENDPOINT: BUSCAR JOGOS
# ============================================================

@app.route("/fixtures", methods=["GET"])
@rate_limit(max_calls=100, period=3600)
@validate_params(["date", "league"])
@cache_response(ttl=300)  # Cache por 5 minutos
def fixtures():
    """
    Busca jogos por data e liga
    Exemplo: /fixtures?date=2025-11-06&league=71&season=2024
    """
    date = request.args.get("date")
    league = request.args.get("league")
    season = request.args.get("season", "2024")
    
    # Validar formato de data
    try:
        datetime.strptime(date, '%Y-%m-%d')
    except ValueError:
        return jsonify({
            "ok": False,
            "error": "Formato de data inválido. Use YYYY-MM-DD",
            "exemplo": "2025-11-06"
        }), 400
    
    data, error = call_api_football("/fixtures", {
        "date": date,
        "league": league,
        "season": season
    })
    
    if data:
        fixtures = data.get("response", [])
        
        # Formatar resposta
        jogos = []
        for fixture in fixtures:
            jogo = {
                "id": fixture["fixture"]["id"],
                "data": fixture["fixture"]["date"],
                "status": fixture["fixture"]["status"]["long"],
                "time_casa": {
                    "id": fixture["teams"]["home"]["id"],
                    "nome": fixture["teams"]["home"]["name"],
                    "logo": fixture["teams"]["home"]["logo"]
                },
                "time_fora": {
                    "id": fixture["teams"]["away"]["id"],
                    "nome": fixture["teams"]["away"]["name"],
                    "logo": fixture["teams"]["away"]["logo"]
                },
                "gols": fixture["goals"]
            }
            jogos.append(jogo)
        
        return jsonify({
            "ok": True,
            "total": len(jogos),
            "jogos": jogos,
            "parametros": {
                "date": date,
                "league": league,
                "season": season
            }
        })
    
    return jsonify({
        "ok": False,
        "error": error or "Erro ao buscar jogos"
    }), 500

# ============================================================
# 🏆 ENDPOINT: CLASSIFICAÇÃO
# ============================================================

@app.route("/standings", methods=["GET"])
@rate_limit(max_calls=100, period=3600)
@validate_params(["league", "season"])
@cache_response(ttl=600)  # Cache por 10 minutos
def standings():
    """
    Busca classificação do campeonato
    Exemplo: /standings?league=71&season=2024
    """
    league = request.args.get("league")
    season = request.args.get("season")
    
    data, error = call_api_football("/standings", {
        "league": league,
        "season": season
    })
    
    if data:
        response = data.get("response", [])
        
        if response and len(response) > 0:
            standings = response[0].get("league", {}).get("standings", [[]])[0]
            
            tabela = []
            for team in standings:
                tabela.append({
                    "posicao": team["rank"],
                    "time": team["team"]["name"],
                    "pontos": team["points"],
                    "jogos": team["all"]["played"],
                    "vitorias": team["all"]["win"],
                    "empates": team["all"]["draw"],
                    "derrotas": team["all"]["lose"],
                    "gols_pro": team["all"]["goals"]["for"],
                    "gols_contra": team["all"]["goals"]["against"],
                    "saldo": team["goalsDiff"],
                    "forma": team.get("form", "")
                })
            
            return jsonify({
                "ok": True,
                "tabela": tabela,
                "liga": response[0]["league"]["name"],
                "temporada": season
            })
    
    return jsonify({
        "ok": False,
        "error": error or "Erro ao buscar classificação"
    }), 500

# ============================================================
# 🔍 ENDPOINT: TIMES
# ============================================================

@app.route("/teams", methods=["GET"])
@rate_limit(max_calls=100, period=3600)
@validate_params(["league"])
@cache_response(ttl=3600)  # Cache por 1 hora
def teams():
    """
    Busca times de uma liga
    Exemplo: /teams?league=71&season=2024
    """
    league = request.args.get("league")
    season = request.args.get("season", "2024")
    
    data, error = call_api_football("/teams", {
        "league": league,
        "season": season
    })
    
    if data:
        teams_list = data.get("response", [])
        
        times = []
        for item in teams_list:
            team = item.get("team", {})
            venue = item.get("venue", {})
            times.append({
                "id": team.get("id"),
                "nome": team.get("name"),
                "logo": team.get("logo"),
                "fundacao": team.get("founded"),
                "estadio": venue.get("name"),
                "capacidade": venue.get("capacity"),
                "cidade": venue.get("city")
            })
        
        return jsonify({
            "ok": True,
            "total": len(times),
            "times": times
        })
    
    return jsonify({
        "ok": False,
        "error": error or "Erro ao buscar times"
    }), 500

# ============================================================
# 📊 ENDPOINT: ESTATÍSTICAS DO TIME
# ============================================================

@app.route("/teams/statistics", methods=["GET"])
@rate_limit(max_calls=100, period=3600)
@validate_params(["team", "league"])
@cache_response(ttl=600)
def team_stats():
    """
    Busca estatísticas de um time
    Exemplo: /teams/statistics?team=121&league=71&season=2024
    """
    team = request.args.get("team")
    league = request.args.get("league")
    season = request.args.get("season", "2024")
    
    data, error = call_api_football("/teams/statistics", {
        "team": team,
        "league": league,
        "season": season
    })
    
    if data:
        response = data.get("response", {})
        
        if response:
            stats = {
                "time": response.get("team", {}).get("name"),
                "forma": response.get("form"),
                "jogos": response.get("fixtures", {}),
                "gols": response.get("goals", {}),
                "maiores": response.get("biggest", {}),
                "clean_sheets": response.get("clean_sheet", {}),
                "penaltis": response.get("penalty", {})
            }
            
            return jsonify({
                "ok": True,
                "estatisticas": stats
            })
    
    return jsonify({
        "ok": False,
        "error": error or "Erro ao buscar estatísticas"
    }), 500

# ============================================================
# ⚽ ENDPOINT: ARTILHEIROS
# ============================================================

@app.route("/players/topscorers", methods=["GET"])
@rate_limit(max_calls=100, period=3600)
@validate_params(["league"])
@cache_response(ttl=3600)
def topscorers():
    """
    Busca artilheiros do campeonato
    Exemplo: /players/topscorers?league=71&season=2024
    """
    league = request.args.get("league")
    season = request.args.get("season", "2024")
    
    data, error = call_api_football("/players/topscorers", {
        "league": league,
        "season": season
    })
    
    if data:
        scorers = data.get("response", [])[:20]  # Top 20
        
        artilheiros = []
        for item in scorers:
            player = item.get("player", {})
            stats = item.get("statistics", [{}])[0]
            
            artilheiros.append({
                "posicao": len(artilheiros) + 1,
                "jogador": player.get("name"),
                "time": stats.get("team", {}).get("name"),
                "gols": stats.get("goals", {}).get("total", 0),
                "assistencias": stats.get("goals", {}).get("assists", 0),
                "jogos": stats.get("games", {}).get("appearences", 0),
                "foto": player.get("photo")
            })
        
        return jsonify({
            "ok": True,
            "total": len(artilheiros),
            "artilheiros": artilheiros,
            "liga": league,
            "temporada": season
        })
    
    return jsonify({
        "ok": False,
        "error": error or "Erro ao buscar artilheiros"
    }), 500

# ============================================================
# 🏠 PÁGINA INICIAL
# ============================================================

@app.route("/", methods=["GET"])
def home():
    """Página inicial com documentação"""
    hoje = datetime.now().strftime('%Y-%m-%d')
    
    return jsonify({
        "🏆": "API Apostas Esportivas Pro",
        "status": "✅ Online",
        "version": "3.0.0",
        "melhorias": [
            "✅ Retry automático em falhas",
            "✅ Cache Redis (opcional)",
            "✅ Logs estruturados",
            "✅ Validação de parâmetros",
            "✅ Rate limiting (100 req/hora)",
            "✅ CORS configurado",
            "✅ Segurança aprimorada"
        ],
        "endpoints_disponiveis": {
            "health": {
                "url": "/health",
                "metodo": "GET",
                "descricao": "Verificar status da API"
            },
            "jogos": {
                "url": "/fixtures",
                "metodo": "GET",
                "params": ["date", "league", "season"],
                "exemplo": f"/fixtures?date={hoje}&league=71&season=2024"
            },
            "classificacao": {
                "url": "/standings",
                "metodo": "GET",
                "params": ["league", "season"],
                "exemplo": "/standings?league=71&season=2024"
            },
            "times": {
                "url": "/teams",
                "metodo": "GET",
                "params": ["league", "season"],
                "exemplo": "/teams?league=71&season=2024"
            },
            "estatisticas_time": {
                "url": "/teams/statistics",
                "metodo": "GET",
                "params": ["team", "league", "season"],
                "exemplo": "/teams/statistics?team=121&league=71&season=2024"
            },
            "artilheiros": {
                "url": "/players/topscorers",
                "metodo": "GET",
                "params": ["league", "season"],
                "exemplo": "/players/topscorers?league=71&season=2024"
            }
        },
        "rate_limit": "100 requisições por hora",
        "cache": "5-60 minutos dependendo do endpoint",
        "documentacao_completa": "/docs (em breve)"
    })

# ============================================================
# 🎛️ TRATAMENTO DE ERROS
# ============================================================

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        "ok": False,
        "error": "Endpoint não encontrado",
        "dica": "Acesse / para ver todos os endpoints disponíveis"
    }), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Erro 500: {str(error)}")
    return jsonify({
        "ok": False,
        "error": "Erro interno do servidor",
        "mensagem": "Tente novamente em alguns instantes"
    }), 500

@app.errorhandler(429)
def rate_limit_exceeded(error):
    return jsonify({
        "ok": False,
        "error": "Rate limit excedido",
        "mensagem": "Você atingiu o limite de 100 requisições por hora. Aguarde e tente novamente."
    }), 429

# ============================================================
# ▶️ INICIALIZAÇÃO
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("🚀 API APOSTAS ESPORTIVAS PRO - v3.0 (Melhorada)")
    print("=" * 60)
    print(f"📍 Porta: {PORT}")
    print(f"🔑 API Key: {'✅ Configurada' if API_KEY else '❌ NÃO configurada'}")
    print(f"🌐 Host: {API_HOST}")
    print(f"🗄️  Redis: {'✅ Conectado' if redis_client else '⚠️  Não disponível'}")
    print(f"🔒 Rate Limit: 100 requisições/hora")
    print(f"💻 Ambiente: {FLASK_ENV}")
    print("=" * 60)
    print("📝 Acesse / para ver a documentação completa")
    print("=" * 60)
    
    app.run(
        host="0.0.0.0", 
        port=PORT, 
        debug=(FLASK_ENV == "development")
    )
