from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import requests
from datetime import datetime
import json

app = Flask(__name__)
CORS(app)

# ============================================================
# 🔐 Config – API-Football (via RapidAPI)
# ============================================================

# Suas variáveis já configuradas no Render
API_KEY = os.getenv("API_KEY")  
API_HOST = os.getenv("API_HOST", "api-football-v1.p.rapidapi.com")

headers_api = {
    "x-rapidapi-key": API_KEY,
    "x-rapidapi-host": API_HOST
}

print(f"🔑 API Key configurada: {bool(API_KEY)}")
print(f"🌐 API Host: {API_HOST}")

# ============================================================
# 🔧 Função para chamar a API-Football
# ============================================================

def call_api_football(endpoint, params):
    """Chama a API-Football e retorna os dados"""
    if not API_KEY:
        return None, "API_KEY não configurada"
    
    # URL correta da API
    url = f"https://{API_HOST}/v3{endpoint}"
    
    try:
        print(f"📡 Chamando: {endpoint} com params: {params}")
        response = requests.get(url, headers=headers_api, params=params, timeout=10)
        
        if response.status_code == 200:
            return response.json(), None
        else:
            error_msg = f"Erro {response.status_code}: {response.text[:200]}"
            print(f"❌ {error_msg}")
            return None, error_msg
            
    except Exception as e:
        error_msg = f"Erro na requisição: {str(e)}"
        print(f"❌ {error_msg}")
        return None, error_msg

# ============================================================
# 📅 Endpoint: Buscar Jogos/Partidas
# ============================================================

@app.route("/fixtures", methods=["GET"])
def fixtures():
    """
    Busca jogos por data e liga
    Exemplo: /fixtures?date=2024-11-05&league=71
    """
    date = request.args.get("date")
    league = request.args.get("league")
    
    if not date or not league:
        return jsonify({
            "ok": False,
            "error": "Parâmetros obrigatórios: date (YYYY-MM-DD) e league (ID)"
        }), 400
    
    data, error = call_api_football("/fixtures", {
        "date": date,
        "league": league
    })
    
    if data:
        # Processa e formata a resposta
        fixtures = data.get("response", [])
        
        return jsonify({
            "ok": True,
            "total": len(fixtures),
            "data": fixtures,
            "parameters": {
                "date": date,
                "league": league
            }
        })
    
    return jsonify({
        "ok": False,
        "error": error
    }), 500

# ============================================================
# 🏆 Endpoint: Classificação
# ============================================================

@app.route("/standings", methods=["GET"])
def standings():
    """
    Busca classificação do campeonato
    Exemplo: /standings?league=71&season=2024
    """
    league = request.args.get("league")
    season = request.args.get("season", "2024")  # Default para 2024
    
    if not league:
        return jsonify({
            "ok": False,
            "error": "Parâmetro obrigatório: league (ID)"
        }), 400
    
    data, error = call_api_football("/standings", {
        "league": league,
        "season": season
    })
    
    if data:
        return jsonify({
            "ok": True,
            "data": data.get("response", []),
            "parameters": {
                "league": league,
                "season": season
            }
        })
    
    return jsonify({
        "ok": False,
        "error": error
    }), 500

# ============================================================
# 💰 Endpoint: Odds/Probabilidades
# ============================================================

@app.route("/odds", methods=["GET"])
def odds():
    """
    Busca odds de uma partida específica
    Exemplo: /odds?fixture=1234567
    """
    fixture = request.args.get("fixture")
    
    if not fixture:
        return jsonify({
            "ok": False,
            "error": "Parâmetro obrigatório: fixture (ID da partida)"
        }), 400
    
    data, error = call_api_football("/odds", {
        "fixture": fixture
    })
    
    if data:
        return jsonify({
            "ok": True,
            "data": data.get("response", [])
        })
    
    return jsonify({
        "ok": False,
        "error": error
    }), 500

# ============================================================
# 📊 Endpoint: Estatísticas do Time
# ============================================================

@app.route("/teams/statistics", methods=["GET"])
def team_stats():
    """
    Busca estatísticas de um time
    Exemplo: /teams/statistics?team=121&league=71&season=2024
    """
    team = request.args.get("team")
    league = request.args.get("league")
    season = request.args.get("season", "2024")
    
    if not team or not league:
        return jsonify({
            "ok": False,
            "error": "Parâmetros obrigatórios: team (ID) e league (ID)"
        }), 400
    
    data, error = call_api_football("/teams/statistics", {
        "team": team,
        "league": league,
        "season": season
    })
    
    if data:
        return jsonify({
            "ok": True,
            "data": data.get("response", {})
        })
    
    return jsonify({
        "ok": False,
        "error": error
    }), 500

# ============================================================
# ⚽ Endpoint: Artilheiros
# ============================================================

@app.route("/players/topscorers", methods=["GET"])
def topscorers():
    """
    Busca artilheiros do campeonato
    Exemplo: /players/topscorers?league=71&season=2024
    """
    league = request.args.get("league")
    season = request.args.get("season", "2024")
    
    if not league:
        return jsonify({
            "ok": False,
            "error": "Parâmetro obrigatório: league (ID)"
        }), 400
    
    data, error = call_api_football("/players/topscorers", {
        "league": league,
        "season": season
    })
    
    if data:
        return jsonify({
            "ok": True,
            "data": data.get("response", [])
        })
    
    return jsonify({
        "ok": False,
        "error": error
    }), 500

# ============================================================
# 🔍 Endpoint: Buscar Times
# ============================================================

@app.route("/teams", methods=["GET"])
def teams():
    """
    Busca times de uma liga
    Exemplo: /teams?league=71&season=2024
    """
    league = request.args.get("league")
    season = request.args.get("season", "2024")
    
    if not league:
        return jsonify({
            "ok": False,
            "error": "Parâmetro obrigatório: league (ID)"
        }), 400
    
    data, error = call_api_football("/teams", {
        "league": league,
        "season": season
    })
    
    if data:
        teams_list = data.get("response", [])
        
        # Formata resposta simplificada
        teams_formatted = []
        for item in teams_list:
            team = item.get("team", {})
            teams_formatted.append({
                "id": team.get("id"),
                "name": team.get("name"),
                "logo": team.get("logo")
            })
        
        return jsonify({
            "ok": True,
            "total": len(teams_formatted),
            "teams": teams_formatted
        })
    
    return jsonify({
        "ok": False,
        "error": error
    }), 500

# ============================================================
# 📈 Health Check
# ============================================================

@app.route("/health", methods=["GET"])
def health():
    """Endpoint para verificar status da API"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "api_key_configured": bool(API_KEY),
        "api_host": API_HOST,
        "version": "2.0.0"
    })

# ============================================================
# 🏠 Página Inicial - Documentação
# ============================================================

@app.route("/", methods=["GET"])
def home():
    hoje = datetime.now().strftime('%Y-%m-%d')
    
    return jsonify({
        "🏆": "API Apostas Esportivas Pro",
        "status": "✅ Online",
        "version": "2.0.0",
        "api_key": "✅ Configurada" if API_KEY else "❌ Não configurada",
        
        "endpoints": {
            "jogos": {
                "url": "/fixtures",
                "params": "date (YYYY-MM-DD), league (ID)",
                "exemplo": f"/fixtures?date={hoje}&league=71"
            },
            "classificacao": {
                "url": "/standings", 
                "params": "league (ID), season (YYYY)",
                "exemplo": "/standings?league=71&season=2024"
            },
            "odds": {
                "url": "/odds",
                "params": "fixture (ID)",
                "exemplo": "/odds?fixture=1234567"
            },
            "estatisticas_time": {
                "url": "/teams/statistics",
                "params": "team (ID), league (ID), season (YYYY)",
                "exemplo": "/teams/statistics?team=121&league=71&season=2024"
            },
            "artilheiros": {
                "url": "/players/topscorers",
                "params": "league (ID), season (YYYY)",
                "exemplo": "/players/topscorers?league=71&season=2024"
            },
            "times": {
                "url": "/teams",
                "params": "league (ID), season (YYYY)",
                "exemplo": "/teams?league=71&season=2024"
            }
        },
        
        "ligas_principais": {
            "Brasil": {
                "71": "Brasileirão Série A",
                "72": "Brasileirão Série B",
                "73": "Copa do Brasil"
            },
            "Europa": {
                "39": "Premier League (Inglaterra)",
                "140": "La Liga (Espanha)",
                "135": "Serie A (Itália)",
                "78": "Bundesliga (Alemanha)",
                "61": "Ligue 1 (França)"
            },
            "Continentais": {
                "2": "UEFA Champions League",
                "3": "UEFA Europa League",
                "13": "Copa Libertadores",
                "11": "Copa Sul-Americana"
            }
        },
        
        "times_brasileiros_ids": {
            "121": "Palmeiras",
            "131": "Corinthians", 
            "126": "São Paulo",
            "127": "Flamengo",
            "124": "Fluminense",
            "1062": "Atlético-MG",
            "120": "Botafogo",
            "128": "Santos"
        },
        
        "links_uteis": {
            "github": "https://github.com/nlsoarez/apostasesportivaspro",
            "render": "https://apostasesportivaspro.onrender.com",
            "api_docs": "https://www.api-football.com/documentation-v3"
        },
        
        "exemplos_prontos": {
            "jogos_hoje_brasileirao": f"/fixtures?date={hoje}&league=71",
            "tabela_brasileirao": "/standings?league=71&season=2024",
            "artilheiros_brasileirao": "/players/topscorers?league=71&season=2024",
            "times_brasileirao": "/teams?league=71&season=2024",
            "estatisticas_palmeiras": "/teams/statistics?team=121&league=71&season=2024"
        },
        
        "instrucoes": "Use os endpoints acima para buscar dados. Todos retornam JSON.",
        "suporte": "Em caso de erro, verifique os parâmetros e tente novamente."
    })

# ============================================================
# 🎛️ Tratamento de Erros
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
    return jsonify({
        "ok": False,
        "error": "Erro interno do servidor",
        "mensagem": "Tente novamente em alguns instantes"
    }), 500

# ============================================================
# ▶️ Inicialização
# ============================================================

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    
    print("=" * 60)
    print("🚀 API APOSTAS ESPORTIVAS PRO - INICIANDO")
    print("=" * 60)
    print(f"📍 Porta: {port}")
    print(f"🔑 API Key: {'✅ Configurada' if API_KEY else '❌ ERRO - Não configurada!'}")
    print(f"🌐 Host: {API_HOST}")
    print(f"📊 URL Local: http://localhost:{port}")
    print(f"☁️  URL Render: https://apostasesportivaspro.onrender.com")
    print("=" * 60)
    
    app.run(host="0.0.0.0", port=port, debug=False)
