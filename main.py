from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import requests
from datetime import datetime
import json

app = Flask(__name__)
CORS(app)

# ============================================================
# 🔐 Config – API-Sports (api-football.com)
# ============================================================

# Sua chave API do dashboard.api-football.com
API_KEY = os.getenv("API_KEY")
API_HOST = os.getenv("API_HOST", "v3.football.api-sports.io")

# Headers corretos para API-Sports
headers_api = {
    "x-apisports-key": API_KEY
}

print(f"🔑 API Key configurada: {'✅' if API_KEY else '❌ NÃO CONFIGURADA'}")
print(f"🌐 API Host: {API_HOST}")

# ============================================================
# 🔧 Função para chamar a API-Football
# ============================================================

def call_api_football(endpoint, params):
    """Chama a API-Football e retorna os dados"""
    
    if not API_KEY:
        return None, "API_KEY não configurada. Configure a variável de ambiente."
    
    url = f"https://{API_HOST}{endpoint}"
    
    try:
        print(f"📡 Chamando: {endpoint}")
        print(f"   Params: {params}")
        
        response = requests.get(
            url, 
            headers=headers_api, 
            params=params, 
            timeout=10
        )
        
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            # Verifica se há erros na resposta
            if data.get("errors") and len(data["errors"]) > 0:
                error_msg = str(data["errors"])
                print(f"❌ Erro da API: {error_msg}")
                return None, error_msg
                
            return data, None
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
    Exemplo: /fixtures?date=2025-11-06&league=71
    """
    date = request.args.get("date")
    league = request.args.get("league")
    
    # Season é importante para a API
    season = request.args.get("season", "2024")
    
    if not date or not league:
        return jsonify({
            "ok": False,
            "error": "Parâmetros obrigatórios: date (YYYY-MM-DD) e league (ID)",
            "exemplo": "/fixtures?date=2025-11-06&league=71"
        }), 400
    
    # Endpoint correto
    data, error = call_api_football("/fixtures", {
        "date": date,
        "league": league,
        "season": season
    })
    
    if data:
        fixtures = data.get("response", [])
        
        # Formata resposta simplificada
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
# 🏆 Endpoint: Classificação
# ============================================================

@app.route("/standings", methods=["GET"])
def standings():
    """
    Busca classificação do campeonato
    Exemplo: /standings?league=71&season=2024
    """
    league = request.args.get("league")
    season = request.args.get("season", "2024")
    
    if not league:
        return jsonify({
            "ok": False,
            "error": "Parâmetro obrigatório: league (ID)",
            "exemplo": "/standings?league=71&season=2024"
        }), 400
    
    data, error = call_api_football("/standings", {
        "league": league,
        "season": season
    })
    
    if data:
        response = data.get("response", [])
        
        # Formata a tabela
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
                    "saldo": team["goalsDiff"]
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
            "error": "Parâmetro obrigatório: league (ID)",
            "exemplo": "/teams?league=71&season=2024"
        }), 400
    
    data, error = call_api_football("/teams", {
        "league": league,
        "season": season
    })
    
    if data:
        teams_list = data.get("response", [])
        
        # Formata resposta simplificada
        times = []
        for item in teams_list:
            team = item.get("team", {})
            times.append({
                "id": team.get("id"),
                "nome": team.get("name"),
                "logo": team.get("logo"),
                "fundacao": team.get("founded"),
                "estadio": item.get("venue", {}).get("name"),
                "capacidade": item.get("venue", {}).get("capacity")
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
            "error": "Parâmetro obrigatório: league (ID)",
            "exemplo": "/players/topscorers?league=71&season=2024"
        }), 400
    
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
            "artilheiros": artilheiros,
            "liga": league,
            "temporada": season
        })
    
    return jsonify({
        "ok": False,
        "error": error or "Erro ao buscar artilheiros"
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
            "error": "Parâmetros obrigatórios: team (ID) e league (ID)",
            "exemplo": "/teams/statistics?team=121&league=71&season=2024"
        }), 400
    
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
                "maiores": {
                    "vitoria_casa": response.get("biggest", {}).get("wins", {}).get("home"),
                    "vitoria_fora": response.get("biggest", {}).get("wins", {}).get("away"),
                    "derrota_casa": response.get("biggest", {}).get("loses", {}).get("home"),
                    "derrota_fora": response.get("biggest", {}).get("loses", {}).get("away")
                },
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
# 📈 Health Check
# ============================================================

@app.route("/health", methods=["GET"])
def health():
    """Endpoint para verificar status da API"""
    
    # Testa a API fazendo uma chamada simples
    test_result = "unknown"
    try:
        response = requests.get(
            f"https://{API_HOST}/status",
            headers=headers_api if API_KEY else {},
            timeout=5
        )
        if response.status_code == 200:
            test_result = "connected"
        else:
            test_result = "error"
    except:
        test_result = "timeout"
    
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "api_key_configured": bool(API_KEY),
        "api_host": API_HOST,
        "api_connection": test_result,
        "version": "2.1.0",
        "platform": "vercel"
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
        "version": "2.1.0",
        "platform": "Vercel",
        "api_sports": {
            "key": "✅ Configurada" if API_KEY else "❌ NÃO configurada",
            "host": API_HOST,
            "dashboard": "https://dashboard.api-football.com"
        },
        
        "endpoints_disponiveis": {
            "jogos": {
                "url": "/fixtures",
                "params": "date (YYYY-MM-DD), league (ID), season (YYYY)",
                "exemplo": f"/fixtures?date={hoje}&league=71&season=2024"
            },
            "classificacao": {
                "url": "/standings", 
                "params": "league (ID), season (YYYY)",
                "exemplo": "/standings?league=71&season=2024"
            },
            "times": {
                "url": "/teams",
                "params": "league (ID), season (YYYY)",
                "exemplo": "/teams?league=71&season=2024"
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
            "health": {
                "url": "/health",
                "descricao": "Verifica status da API"
            }
        },
        
        "ligas_principais": {
            "Brasil": {
                "71": "Brasileirão Série A",
                "72": "Brasileirão Série B", 
                "73": "Copa do Brasil",
                "75": "Campeonato Carioca",
                "76": "Campeonato Paulista",
                "77": "Campeonato Mineiro"
            },
            "Europa": {
                "39": "Premier League (Inglaterra)",
                "140": "La Liga (Espanha)",
                "135": "Serie A (Itália)",
                "78": "Bundesliga (Alemanha)",
                "61": "Ligue 1 (França)",
                "94": "Primeira Liga (Portugal)"
            },
            "Competicoes_Internacionais": {
                "2": "UEFA Champions League",
                "3": "UEFA Europa League",
                "13": "Copa Libertadores",
                "11": "Copa Sul-Americana",
                "1": "Mundial de Clubes"
            }
        },
        
        "times_brasileiros": {
            "121": "Palmeiras",
            "131": "Corinthians",
            "126": "São Paulo",
            "127": "Flamengo",
            "124": "Fluminense",
            "1062": "Atlético-MG",
            "120": "Botafogo",
            "128": "Santos",
            "130": "Grêmio",
            "119": "Internacional",
            "134": "Coritiba",
            "1061": "Athletico-PR",
            "132": "Vasco",
            "133": "Cruzeiro",
            "151": "Bahia",
            "154": "Fortaleza"
        },
        
        "exemplos_prontos": {
            "jogos_hoje_brasileirao": f"/fixtures?date={hoje}&league=71&season=2024",
            "tabela_brasileirao": "/standings?league=71&season=2024",
            "times_brasileirao": "/teams?league=71&season=2024",
            "artilheiros_brasileirao": "/players/topscorers?league=71&season=2024",
            "estatisticas_palmeiras": "/teams/statistics?team=121&league=71&season=2024",
            "jogos_champions": f"/fixtures?date={hoje}&league=2&season=2024",
            "tabela_premier": "/standings?league=39&season=2024"
        },
        
        "instrucoes": "Use os endpoints acima para buscar dados. Todos retornam JSON.",
        "limite_api": "Verifique seu limite diário em dashboard.api-football.com"
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
# 🔧 Configuração para Vercel
# ============================================================

# Adicionar middleware para Vercel
from werkzeug.middleware.proxy_fix import ProxyFix
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

# ============================================================
# ▶️ Inicialização
# ============================================================

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    
    print("=" * 60)
    print("🚀 API APOSTAS ESPORTIVAS PRO - v2.1")
    print("=" * 60)
    print(f"📍 Porta: {port}")
    print(f"🔑 API Key: {'✅ Configurada' if API_KEY else '❌ NÃO configurada'}")
    print(f"🌐 Host: {API_HOST}")
    print(f"📊 Dashboard: https://dashboard.api-football.com")
    print(f"💻 Local: http://localhost:{port}")
    print(f"☁️  Vercel: Pronto para deploy")
    print("=" * 60)
    print("📝 Acesse / para ver a documentação completa")
    print("=" * 60)
    
    app.run(host="0.0.0.0", port=port, debug=False)
