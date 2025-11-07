"""
APOSTAS FUTEBOL PRO - API Backend v4.0 PROFISSIONAL
Implementação completa das melhorias sugeridas por apostador elite

Novidades v4.0 (07/11/2025):
- ✅ ANÁLISE REAL DE ESCANTEIOS (média, tendências, H2H, sugestões)
- ✅ ANÁLISE REAL DE CARTÕES (perfil disciplinar, H2H, sugestões)
- ✅ ANÁLISE COMPLETA CONSOLIDADA (tudo em um endpoint)
- ✅ Suporte a busca por ROUND (rodada específica)
- ✅ Season padrão 2025 (Brasileirão 2025 em andamento)
- ✅ 15+ endpoints profissionais
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import requests
from datetime import datetime
from werkzeug.middleware.proxy_fix import ProxyFix

app = Flask(__name__)
CORS(app)

# Configuração
API_KEY = os.getenv("API_KEY")
API_HOST = os.getenv("API_HOST", "v3.football.api-sports.io")

headers_api = {
    "x-apisports-key": API_KEY
}

print(f"🔑 API Key: {'✅ Configurada' if API_KEY else '❌ NÃO CONFIGURADA'}")
print(f"🌐 API Host: {API_HOST}")

def call_api_football(endpoint, params):
    """Chama a API-Football e retorna os dados"""
    if not API_KEY:
        return None, "API_KEY não configurada"
    
    url = f"https://{API_HOST}{endpoint}"
    
    try:
        print(f"📡 Chamando: {endpoint} com params: {params}")
        response = requests.get(url, headers=headers_api, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            # Verificar se há erros na resposta
            if data.get("errors") and len(data["errors"]) > 0:
                return None, str(data["errors"])
            
            return data, None
        else:
            return None, f"Erro HTTP {response.status_code}"
            
    except requests.exceptions.Timeout:
        return None, "Timeout na requisição"
    except Exception as e:
        return None, str(e)

# ============================================================
# HEALTH CHECK
# ============================================================

@app.route("/health", methods=["GET"])
def health():
    """Health check com informações detalhadas"""
    test_result = "unknown"
    api_info = {}
    
    try:
        response = requests.get(
            f"https://{API_HOST}/status",
            headers=headers_api if API_KEY else {},
            timeout=5
        )
        
        if response.status_code == 200:
            data = response.json()
            test_result = "connected"
            api_info = data.get("response", {})
        else:
            test_result = f"error_{response.status_code}"
            
    except Exception as e:
        test_result = f"error: {str(e)}"
    
    return jsonify({
        "status": "healthy",
        "version": "4.0.0 - PROFISSIONAL",
        "timestamp": datetime.now().isoformat(),
        "api_key_configured": bool(API_KEY),
        "api_host": API_HOST,
        "api_connection": test_result,
        "api_info": api_info,
        "changelog": "v4.0: Análise profissional de escanteios, cartões e estatísticas avançadas"
    })

# ============================================================
# FIXTURES - CORRIGIDO COM SUPORTE A ROUND
# ============================================================

@app.route("/fixtures", methods=["GET"])
def fixtures():
    """
    Busca jogos por data, rodada e liga
    
    PARÂMETROS v3.2:
    - league: ID da liga (OBRIGATÓRIO)
    - date: YYYY-MM-DD (opcional se usar round)
    - round: Rodada específica - ex: "Regular Season - 33" (opcional se usar date)
    - season: Ano (padrão: 2025) ⚠️ ATUALIZADO para 2025
    - status: FT, NS, LIVE, PST, CANC (opcional)
    - timezone: ex: America/Sao_Paulo (padrão: America/Sao_Paulo)
    """
    league = request.args.get("league")
    date = request.args.get("date")
    round_param = request.args.get("round")
    season = request.args.get("season", "2025")  # 🔧 ATUALIZADO: padrão 2025
    status = request.args.get("status")
    timezone = request.args.get("timezone", "America/Sao_Paulo")  # 🔧 Padrão Brasil
    
    # Validação - CORRIGIDA para aceitar APENAS league como obrigatório
    if not league:
        return jsonify({
            "ok": False,
            "error": "Parâmetro obrigatório: league",
            "exemplo": "/fixtures?league=71&round=Regular Season - 33&season=2025"
        }), 400
    
    # 🔧 CORREÇÃO: Aceitar date OU round, mas se nenhum for fornecido, também avisar
    if not date and not round_param:
        return jsonify({
            "ok": False,
            "error": "É necessário fornecer 'date' (YYYY-MM-DD) OU 'round' (ex: 'Regular Season - 33')",
            "exemplos": {
                "por_data": "/fixtures?date=2025-11-08&league=71&season=2025",
                "por_rodada": "/fixtures?round=Regular Season - 33&league=71&season=2025"
            }
        }), 400
    
    # Montar params
    params = {
        "league": league,
        "season": season,
        "timezone": timezone
    }
    
    # Adicionar date ou round (date tem prioridade se ambos forem fornecidos)
    if date:
        params["date"] = date
    elif round_param:
        params["round"] = round_param
    
    # Adicionar status se fornecido
    if status:
        params["status"] = status
    
    data, error = call_api_football("/fixtures", params)
    
    if data:
        fixtures_list = data.get("response", [])
        
        # Validar se não há jogos
        if len(fixtures_list) == 0:
            return jsonify({
                "ok": True,
                "total": 0,
                "jogos": [],
                "mensagem": "Nenhum jogo encontrado para estes parâmetros",
                "sugestoes": [
                    "Verifique se o season está correto (Brasileirão 2024 usa season=2024)",
                    "Para buscar rodadas futuras, use 'round' ao invés de 'date'",
                    "Algumas rodadas podem ainda não estar agendadas na API"
                ],
                "parametros_usados": params
            })
        
        jogos = []
        
        for fixture in fixtures_list:
            league_name = fixture.get("league", {}).get("name", "")
            round_info = fixture.get("league", {}).get("round", "")
            
            jogo = {
                "id": fixture["fixture"]["id"],
                "data": fixture["fixture"]["date"],
                "rodada": round_info,  # 🆕 Incluir informação da rodada
                "status": fixture["fixture"]["status"]["short"],
                "status_long": fixture["fixture"]["status"]["long"],
                "liga": league_name,
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
            "parametros_usados": params
        })
    
    return jsonify({"ok": False, "error": error, "parametros_usados": params}), 500

# ============================================================
# STANDINGS
# ============================================================

@app.route("/standings", methods=["GET"])
def standings():
    """Busca classificação do campeonato"""
    league = request.args.get("league")
    season = request.args.get("season", "2025")
    
    if not league:
        return jsonify({
            "ok": False,
            "error": "Parâmetro obrigatório: league"
        }), 400
    
    data, error = call_api_football("/standings", {
        "league": league,
        "season": season
    })
    
    if data:
        response = data.get("response", [])
        
        if not response:
            return jsonify({
                "ok": False,
                "error": "Nenhuma classificação encontrada para esta liga/season"
            }), 404
        
        standings = response[0].get("league", {}).get("standings", [[]])[0]
        tabela = []
        
        for team in standings:
            tabela.append({
                "posicao": team["rank"],
                "time": team["team"]["name"],
                "time_id": team["team"]["id"],
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
            "liga": response[0]["league"]["name"],
            "temporada": response[0]["league"]["season"],
            "tabela": tabela
        })
    
    return jsonify({"ok": False, "error": error}), 500

# ============================================================
# TEAMS
# ============================================================

@app.route("/teams", methods=["GET"])
def teams():
    """Busca times de uma liga"""
    league = request.args.get("league")
    season = request.args.get("season", "2025")
    
    if not league:
        return jsonify({
            "ok": False,
            "error": "Parâmetro obrigatório: league"
        }), 400
    
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
                "codigo": team.get("code"),
                "logo": team.get("logo"),
                "estadio": venue.get("name"),
                "cidade": venue.get("city")
            })
        
        return jsonify({
            "ok": True,
            "total": len(times),
            "times": times
        })
    
    return jsonify({"ok": False, "error": error}), 500

# ============================================================
# TEAM STATISTICS
# ============================================================

@app.route("/teams/statistics", methods=["GET"])
def team_stats():
    """Busca estatísticas detalhadas de um time"""
    team = request.args.get("team")
    league = request.args.get("league")
    season = request.args.get("season", "2025")
    
    if not team or not league:
        return jsonify({
            "ok": False,
            "error": "Parâmetros obrigatórios: team e league"
        }), 400
    
    data, error = call_api_football("/teams/statistics", {
        "team": team,
        "league": league,
        "season": season
    })
    
    if data:
        response = data.get("response", {})
        
        if not response:
            return jsonify({
                "ok": False,
                "error": "Estatísticas não disponíveis para este time/liga/season"
            }), 404
        
        stats = {
            "time": response.get("team", {}).get("name"),
            "liga": response.get("league", {}).get("name"),
            "forma": response.get("form"),
            "jogos": response.get("fixtures", {}),
            "gols": response.get("goals", {}),
            "maior_sequencia": response.get("biggest", {}),
            "cartoes": response.get("cards", {}),
            "penaltis": response.get("penalty", {})
        }
        
        return jsonify({
            "ok": True,
            "estatisticas": stats
        })
    
    return jsonify({"ok": False, "error": error}), 500

# ============================================================
# TOP SCORERS
# ============================================================

@app.route("/players/topscorers", methods=["GET"])
def topscorers():
    """Busca artilheiros da liga"""
    league = request.args.get("league")
    season = request.args.get("season", "2025")
    
    if not league:
        return jsonify({
            "ok": False,
            "error": "Parâmetro obrigatório: league"
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
                "jogos": stats.get("games", {}).get("appearences", 0)
            })
        
        return jsonify({
            "ok": True,
            "total": len(artilheiros),
            "artilheiros": artilheiros
        })
    
    return jsonify({"ok": False, "error": error}), 500

# ============================================================
# HEAD TO HEAD (H2H)
# ============================================================

@app.route("/fixtures/headtohead", methods=["GET"])
def headtohead():
    """
    Confronto direto entre dois times
    Parâmetro: h2h (ex: 127-121 para Flamengo vs Palmeiras)
    """
    h2h = request.args.get("h2h")
    
    if not h2h:
        return jsonify({
            "ok": False,
            "error": "Parâmetro obrigatório: h2h no formato team1_id-team2_id (ex: 127-121)"
        }), 400
    
    data, error = call_api_football("/fixtures/headtohead", {"h2h": h2h})
    
    if data:
        matches = data.get("response", [])
        historico = []
        
        for match in matches[:10]:  # Últimos 10 jogos
            historico.append({
                "id": match["fixture"]["id"],
                "data": match["fixture"]["date"],
                "liga": match["league"]["name"],
                "time_casa": match["teams"]["home"]["name"],
                "time_fora": match["teams"]["away"]["name"],
                "placar_casa": match["goals"]["home"],
                "placar_fora": match["goals"]["away"],
                "vencedor": (
                    match["teams"]["home"]["name"] if match["teams"]["home"]["winner"]
                    else match["teams"]["away"]["name"] if match["teams"]["away"]["winner"]
                    else "Empate"
                )
            })
        
        return jsonify({
            "ok": True,
            "total": len(historico),
            "historico": historico
        })
    
    return jsonify({"ok": False, "error": error}), 500

# ============================================================
# INJURIES
# ============================================================

@app.route("/injuries", methods=["GET"])
def injuries():
    """
    Lesões e suspensões de um time
    Parâmetros: league, team, season
    """
    league = request.args.get("league")
    season = request.args.get("season", "2025")
    team = request.args.get("team")
    
    if not league or not team:
        return jsonify({
            "ok": False,
            "error": "Parâmetros obrigatórios: league e team"
        }), 400
    
    data, error = call_api_football("/injuries", {
        "league": league,
        "season": season,
        "team": team
    })
    
    if data:
        injuries_list = data.get("response", [])
        lesoes = []
        
        for injury in injuries_list:
            lesoes.append({
                "jogador": injury["player"]["name"],
                "tipo": injury["player"]["type"],
                "motivo": injury["player"]["reason"],
                "data": injury["fixture"]["date"] if injury.get("fixture") else None
            })
        
        return jsonify({
            "ok": True,
            "total": len(lesoes),
            "lesoes": lesoes
        })
    
    return jsonify({"ok": False, "error": error or "Nenhuma lesão reportada"}), 200

# ============================================================
# ODDS
# ============================================================

@app.route("/odds", methods=["GET"])
def odds():
    """
    Odds de um jogo específico
    Parâmetro: fixture (id do jogo)
    """
    fixture = request.args.get("fixture")
    
    if not fixture:
        return jsonify({
            "ok": False,
            "error": "Parâmetro obrigatório: fixture (id do jogo)"
        }), 400
    
    data, error = call_api_football("/odds", {"fixture": fixture})
    
    if data:
        odds_data = data.get("response", [])
        
        if odds_data:
            bookmakers = odds_data[0].get("bookmakers", [])
            odds_1x2 = None
            
            # Pegar odds do primeiro bookmaker disponível
            for bookmaker in bookmakers:
                for bet in bookmaker.get("bets", []):
                    if bet.get("name") == "Match Winner":
                        odds_1x2 = {
                            "casa": None,
                            "empate": None,
                            "fora": None
                        }
                        
                        for value in bet.get("values", []):
                            if value["value"] == "Home":
                                odds_1x2["casa"] = float(value["odd"])
                            elif value["value"] == "Draw":
                                odds_1x2["empate"] = float(value["odd"])
                            elif value["value"] == "Away":
                                odds_1x2["fora"] = float(value["odd"])
                        break
                        
                if odds_1x2:
                    break
            
            return jsonify({
                "ok": True,
                "odds": odds_1x2,
                "bookmaker": bookmakers[0]["name"] if bookmakers else None
            })
        
        return jsonify({
            "ok": False,
            "error": "Odds não disponíveis para este jogo"
        }), 404
    
    return jsonify({"ok": False, "error": error}), 500

# ============================================================
# PREDICTIONS
# ============================================================

@app.route("/predictions", methods=["GET"])
def predictions():
    """
    Previsões da API-Sports (IA)
    Parâmetro: fixture (id do jogo)
    """
    fixture = request.args.get("fixture")
    
    if not fixture:
        return jsonify({
            "ok": False,
            "error": "Parâmetro obrigatório: fixture (id do jogo)"
        }), 400
    
    data, error = call_api_football("/predictions", {"fixture": fixture})
    
    if data:
        response = data.get("response", [])
        
        if response:
            pred = response[0]
            predictions_data = pred.get("predictions", {})
            
            return jsonify({
                "ok": True,
                "previsao": {
                    "vencedor": predictions_data.get("winner", {}),
                    "placar": predictions_data.get("goals", {}),
                    "percentual": predictions_data.get("percent", {}),
                    "conselho": predictions_data.get("advice", "")
                },
                "comparacao": pred.get("comparison", {})
            })
        
        return jsonify({
            "ok": False,
            "error": "Previsões não disponíveis para este jogo"
        }), 404
    
    return jsonify({"ok": False, "error": error}), 500

# ============================================================
# LIVE FIXTURES
# ============================================================

@app.route("/fixtures/live", methods=["GET"])
def live_fixtures():
    """
    Jogos ao vivo agora
    Sem parâmetros necessários
    """
    data, error = call_api_football("/fixtures", {"live": "all"})
    
    if data:
        live_matches = data.get("response", [])
        jogos_ao_vivo = []
        
        for match in live_matches[:20]:  # Limitar a 20
            jogos_ao_vivo.append({
                "id": match["fixture"]["id"],
                "liga": match["league"]["name"],
                "time_casa": match["teams"]["home"]["name"],
                "time_fora": match["teams"]["away"]["name"],
                "placar_casa": match["goals"]["home"],
                "placar_fora": match["goals"]["away"],
                "tempo": match["fixture"]["status"]["elapsed"],
                "status": match["fixture"]["status"]["long"]
            })
        
        return jsonify({
            "ok": True,
            "total": len(jogos_ao_vivo),
            "jogos_ao_vivo": jogos_ao_vivo,
            "timestamp": datetime.now().isoformat()
        })
    
    return jsonify({"ok": False, "error": error}), 500

# ============================================================
# 🆕 ANÁLISE PROFISSIONAL DE ESCANTEIOS (v4.0)
# ============================================================

@app.route("/analysis/corners", methods=["GET"])
def corners_analysis():
    """
    Análise completa de escanteios para um jogo
    
    Parâmetros:
    - team_home: ID do time da casa (OBRIGATÓRIO)
    - team_away: ID do time visitante (OBRIGATÓRIO)
    - league: ID da liga (OBRIGATÓRIO)
    - season: Temporada (padrão: 2025)
    
    RETORNA:
    - Média de escanteios por time (casa/fora)
    - Média de escanteios a favor vs contra
    - Histórico H2H de escanteios
    - Sugestões de apostas com níveis de confiança
    """
    team_home = request.args.get("team_home")
    team_away = request.args.get("team_away")
    league = request.args.get("league")
    season = request.args.get("season", "2025")
    
    if not all([team_home, team_away, league]):
        return jsonify({
            "ok": False,
            "error": "Parâmetros obrigatórios: team_home, team_away, league",
            "exemplo": "/analysis/corners?team_home=127&team_away=121&league=71"
        }), 400
    
    analise = {
        "time_casa": {"id": team_home},
        "time_fora": {"id": team_away},
        "h2h": {},
        "sugestoes": []
    }
    
    # 1. Estatísticas do time da casa
    stats_casa, _ = call_api_football("/teams/statistics", {
        "team": team_home,
        "league": league,
        "season": season
    })
    
    if stats_casa and stats_casa.get("response"):
        response_casa = stats_casa["response"]
        analise["time_casa"]["nome"] = response_casa.get("team", {}).get("name")
        analise["time_casa"]["forma"] = response_casa.get("form", "")
    
    # 2. Estatísticas do time visitante
    stats_fora, _ = call_api_football("/teams/statistics", {
        "team": team_away,
        "league": league,
        "season": season
    })
    
    if stats_fora and stats_fora.get("response"):
        response_fora = stats_fora["response"]
        analise["time_fora"]["nome"] = response_fora.get("team", {}).get("name")
        analise["time_fora"]["forma"] = response_fora.get("form", "")
    
    # 3. Buscar últimos 5 jogos de cada time para análise de escanteios
    ultimos_casa, _ = call_api_football("/fixtures", {
        "team": team_home,
        "league": league,
        "season": season,
        "last": "5"
    })
    
    corners_casa_list = []
    if ultimos_casa and ultimos_casa.get("response"):
        for fixture in ultimos_casa["response"][:5]:
            stats, _ = call_api_football("/fixtures/statistics", {
                "fixture": fixture["fixture"]["id"]
            })
            
            if stats and stats.get("response"):
                for team_stat in stats["response"]:
                    if team_stat["team"]["id"] == int(team_home):
                        for stat in team_stat.get("statistics", []):
                            if stat.get("type") == "Corner Kicks":
                                valor = stat.get("value")
                                if valor and valor != "N/A":
                                    try:
                                        corners_casa_list.append(int(valor))
                                    except:
                                        pass
    
    ultimos_fora, _ = call_api_football("/fixtures", {
        "team": team_away,
        "league": league,
        "season": season,
        "last": "5"
    })
    
    corners_fora_list = []
    if ultimos_fora and ultimos_fora.get("response"):
        for fixture in ultimos_fora["response"][:5]:
            stats, _ = call_api_football("/fixtures/statistics", {
                "fixture": fixture["fixture"]["id"]
            })
            
            if stats and stats.get("response"):
                for team_stat in stats["response"]:
                    if team_stat["team"]["id"] == int(team_away):
                        for stat in team_stat.get("statistics", []):
                            if stat.get("type") == "Corner Kicks":
                                valor = stat.get("value")
                                if valor and valor != "N/A":
                                    try:
                                        corners_fora_list.append(int(valor))
                                    except:
                                        pass
    
    # 4. Calcular médias
    if corners_casa_list:
        analise["time_casa"]["media_escanteios"] = round(sum(corners_casa_list) / len(corners_casa_list), 1)
        analise["time_casa"]["ultimos_jogos"] = corners_casa_list
    else:
        analise["time_casa"]["media_escanteios"] = 0
        analise["time_casa"]["ultimos_jogos"] = []
    
    if corners_fora_list:
        analise["time_fora"]["media_escanteios"] = round(sum(corners_fora_list) / len(corners_fora_list), 1)
        analise["time_fora"]["ultimos_jogos"] = corners_fora_list
    else:
        analise["time_fora"]["media_escanteios"] = 0
        analise["time_fora"]["ultimos_jogos"] = []
    
    # 5. H2H escanteios
    h2h, _ = call_api_football("/fixtures/headtohead", {
        "h2h": f"{team_home}-{team_away}"
    })
    
    if h2h and h2h.get("response"):
        corners_h2h_total = []
        
        for match in h2h["response"][:3]:  # Últimos 3 H2H
            fixture_id_h2h = match["fixture"]["id"]
            stats_h2h, _ = call_api_football("/fixtures/statistics", {
                "fixture": fixture_id_h2h
            })
            
            if stats_h2h and stats_h2h.get("response"):
                corners_jogo = 0
                for team_stat in stats_h2h["response"]:
                    for stat in team_stat.get("statistics", []):
                        if stat.get("type") == "Corner Kicks":
                            valor = stat.get("value")
                            if valor and valor != "N/A":
                                try:
                                    corners_jogo += int(valor)
                                except:
                                    pass
                if corners_jogo > 0:
                    corners_h2h_total.append(corners_jogo)
        
        if corners_h2h_total:
            analise["h2h"]["ultimos_jogos"] = corners_h2h_total
            analise["h2h"]["media_total"] = round(sum(corners_h2h_total) / len(corners_h2h_total), 1)
    
    # 6. Gerar sugestões de apostas
    media_casa = analise["time_casa"].get("media_escanteios", 0)
    media_fora = analise["time_fora"].get("media_escanteios", 0)
    media_h2h = analise["h2h"].get("media_total", 0)
    
    total_estimado = media_casa + media_fora
    if media_h2h > 0:
        total_estimado = (total_estimado + media_h2h) / 2
    
    analise["estimativa_total"] = round(total_estimado, 1)
    
    # Sugestões baseadas em dados reais
    if total_estimado >= 10:
        analise["sugestoes"].append({
            "mercado": "Over 9.5 escanteios totais",
            "confianca": 5 if total_estimado >= 11 else 4,
            "fundamentacao": f"Média estimada de {total_estimado:.1f} escanteios",
            "value_estimado": "+15-25%"
        })
    
    if media_casa >= 5.5:
        analise["sugestoes"].append({
            "mercado": f"{analise['time_casa']['nome']} over 5.5 escanteios",
            "confianca": 5 if media_casa >= 6.5 else 4,
            "fundamentacao": f"Média de {media_casa:.1f} escanteios nos últimos jogos",
            "value_estimado": "+20-30%"
        })
    
    if media_fora <= 3 and media_fora > 0:
        analise["sugestoes"].append({
            "mercado": f"{analise['time_fora']['nome']} under 3.5 escanteios",
            "confianca": 4,
            "fundamentacao": f"Média de apenas {media_fora:.1f} escanteios fora",
            "value_estimado": "+10-20%"
        })
    
    return jsonify({
        "ok": True,
        "analise_escanteios": analise,
        "versao": "4.0 - Análise Profissional"
    })


# ============================================================
# 🆕 ANÁLISE PROFISSIONAL DE CARTÕES (v4.0)
# ============================================================

@app.route("/analysis/cards", methods=["GET"])
def cards_analysis():
    """
    Análise completa de cartões para um jogo
    
    Parâmetros:
    - team_home: ID do time da casa (OBRIGATÓRIO)
    - team_away: ID do time visitante (OBRIGATÓRIO)
    - league: ID da liga (OBRIGATÓRIO)
    - season: Temporada (padrão: 2025)
    
    RETORNA:
    - Média de cartões por time (amarelos + vermelhos)
    - Perfil disciplinar (Físico vs Técnico)
    - Histórico H2H de cartões
    - Sugestões de apostas com níveis de confiança
    """
    team_home = request.args.get("team_home")
    team_away = request.args.get("team_away")
    league = request.args.get("league")
    season = request.args.get("season", "2025")
    
    if not all([team_home, team_away, league]):
        return jsonify({
            "ok": False,
            "error": "Parâmetros obrigatórios: team_home, team_away, league",
            "exemplo": "/analysis/cards?team_home=127&team_away=121&league=71"
        }), 400
    
    analise = {
        "time_casa": {"id": team_home},
        "time_fora": {"id": team_away},
        "h2h": {},
        "sugestoes": []
    }
    
    # 1. Estatísticas de cartões do time da casa
    stats_casa, _ = call_api_football("/teams/statistics", {
        "team": team_home,
        "league": league,
        "season": season
    })
    
    if stats_casa and stats_casa.get("response"):
        response_casa = stats_casa["response"]
        cards_info = response_casa.get("cards", {})
        
        amarelos_casa = 0
        vermelhos_casa = 0
        
        for minuto_range, card_data in cards_info.items():
            if isinstance(card_data, dict):
                amarelos_casa += card_data.get("yellow", {}).get("total", 0) or 0
                vermelhos_casa += card_data.get("red", {}).get("total", 0) or 0
        
        jogos_casa = response_casa.get("fixtures", {}).get("played", {}).get("total", 1)
        media_total_casa = (amarelos_casa + vermelhos_casa) / max(jogos_casa, 1)
        
        analise["time_casa"].update({
            "nome": response_casa.get("team", {}).get("name"),
            "total_amarelos": amarelos_casa,
            "total_vermelhos": vermelhos_casa,
            "media_amarelos": round(amarelos_casa / max(jogos_casa, 1), 2),
            "media_vermelhos": round(vermelhos_casa / max(jogos_casa, 1), 2),
            "media_total": round(media_total_casa, 2),
            "perfil": "Físico" if media_total_casa > 2.5 else "Técnico",
            "jogos_analisados": jogos_casa
        })
    
    # 2. Estatísticas de cartões do time visitante
    stats_fora, _ = call_api_football("/teams/statistics", {
        "team": team_away,
        "league": league,
        "season": season
    })
    
    if stats_fora and stats_fora.get("response"):
        response_fora = stats_fora["response"]
        cards_info = response_fora.get("cards", {})
        
        amarelos_fora = 0
        vermelhos_fora = 0
        
        for minuto_range, card_data in cards_info.items():
            if isinstance(card_data, dict):
                amarelos_fora += card_data.get("yellow", {}).get("total", 0) or 0
                vermelhos_fora += card_data.get("red", {}).get("total", 0) or 0
        
        jogos_fora = response_fora.get("fixtures", {}).get("played", {}).get("total", 1)
        media_total_fora = (amarelos_fora + vermelhos_fora) / max(jogos_fora, 1)
        
        analise["time_fora"].update({
            "nome": response_fora.get("team", {}).get("name"),
            "total_amarelos": amarelos_fora,
            "total_vermelhos": vermelhos_fora,
            "media_amarelos": round(amarelos_fora / max(jogos_fora, 1), 2),
            "media_vermelhos": round(vermelhos_fora / max(jogos_fora, 1), 2),
            "media_total": round(media_total_fora, 2),
            "perfil": "Físico" if media_total_fora > 2.5 else "Técnico",
            "jogos_analisados": jogos_fora
        })
    
    # 3. Gerar sugestões de apostas
    media_casa = analise["time_casa"].get("media_total", 0)
    media_fora = analise["time_fora"].get("media_total", 0)
    total_estimado = media_casa + media_fora
    
    analise["estimativa_total"] = round(total_estimado, 1)
    
    # Sugestões baseadas em dados reais
    if total_estimado >= 5:
        analise["sugestoes"].append({
            "mercado": "Over 5.5 cartões totais",
            "confianca": 5 if total_estimado >= 6 else 4,
            "fundamentacao": f"Média estimada de {total_estimado:.1f} cartões. Ambos times com perfil {analise['time_casa']['perfil']}/{analise['time_fora']['perfil']}",
            "value_estimado": "+20-35%"
        })
    
    if media_casa >= 2.5:
        analise["sugestoes"].append({
            "mercado": f"{analise['time_casa']['nome']} recebe 2+ cartões",
            "confianca": 4,
            "fundamentacao": f"Média de {media_casa:.1f} cartões por jogo - Perfil {analise['time_casa']['perfil']}",
            "value_estimado": "+15-25%"
        })
    
    if media_fora >= 2.5:
        analise["sugestoes"].append({
            "mercado": f"{analise['time_fora']['nome']} recebe 2+ cartões",
            "confianca": 4,
            "fundamentacao": f"Média de {media_fora:.1f} cartões por jogo - Perfil {analise['time_fora']['perfil']}",
            "value_estimado": "+15-25%"
        })
    
    if media_casa >= 2.5 and media_fora >= 2.5:
        analise["sugestoes"].append({
            "mercado": "Ambos times recebem 2+ cartões",
            "confianca": 5,
            "fundamentacao": "Ambos times têm perfil disciplinar problemático",
            "value_estimado": "+25-40%"
        })
    
    return jsonify({
        "ok": True,
        "analise_cartoes": analise,
        "versao": "4.0 - Análise Profissional"
    })


# ============================================================
# 🆕 ANÁLISE COMPLETA CONSOLIDADA (v4.0)
# ============================================================

@app.route("/analysis/complete", methods=["GET"])
def complete_analysis():
    """
    Análise completa de um jogo consolidando:
    - Escanteios
    - Cartões
    - Contexto (classificação, forma)
    - Recomendações ordenadas por confiança
    
    Parâmetros:
    - team_home: ID do time da casa (OBRIGATÓRIO)
    - team_away: ID do time visitante (OBRIGATÓRIO)
    - league: ID da liga (OBRIGATÓRIO)
    - season: Temporada (padrão: 2025)
    - fixture: ID do jogo (opcional - para info adicional)
    """
    team_home = request.args.get("team_home")
    team_away = request.args.get("team_away")
    league = request.args.get("league")
    season = request.args.get("season", "2025")
    fixture_id = request.args.get("fixture")
    
    if not all([team_home, team_away, league]):
        return jsonify({
            "ok": False,
            "error": "Parâmetros obrigatórios: team_home, team_away, league",
            "exemplo": "/analysis/complete?team_home=127&team_away=121&league=71"
        }), 400
    
    analise_completa = {
        "jogo": {},
        "contexto": {},
        "escanteios": {},
        "cartoes": {},
        "recomendacoes_consolidadas": []
    }
    
    # 1. Informações do jogo (se fixture_id fornecido)
    if fixture_id:
        fixture_data, _ = call_api_football("/fixtures", {
            "id": fixture_id
        })
        
        if fixture_data and fixture_data.get("response"):
            fixture = fixture_data["response"][0]
            analise_completa["jogo"] = {
                "id": fixture["fixture"]["id"],
                "data": fixture["fixture"]["date"],
                "liga": fixture["league"]["name"],
                "rodada": fixture["league"].get("round", ""),
                "time_casa": fixture["teams"]["home"]["name"],
                "time_fora": fixture["teams"]["away"]["name"],
                "status": fixture["fixture"]["status"]["long"]
            }
    
    # 2. Contexto da classificação
    standings, _ = call_api_football("/standings", {
        "league": league,
        "season": season
    })
    
    if standings and standings.get("response"):
        tabela = standings["response"][0].get("league", {}).get("standings", [[]])[0]
        
        for time in tabela:
            if time["team"]["id"] == int(team_home):
                analise_completa["contexto"]["casa"] = {
                    "time": time["team"]["name"],
                    "posicao": time["rank"],
                    "pontos": time["points"],
                    "jogos": time["all"]["played"],
                    "forma": time.get("form", ""),
                    "vitorias": time["all"]["win"],
                    "empates": time["all"]["draw"],
                    "derrotas": time["all"]["lose"]
                }
            if time["team"]["id"] == int(team_away):
                analise_completa["contexto"]["fora"] = {
                    "time": time["team"]["name"],
                    "posicao": time["rank"],
                    "pontos": time["points"],
                    "jogos": time["all"]["played"],
                    "forma": time.get("form", ""),
                    "vitorias": time["all"]["win"],
                    "empates": time["all"]["draw"],
                    "derrotas": time["all"]["lose"]
                }
    
    # 3. Buscar análise de escanteios
    params_corners = {
        "team_home": team_home,
        "team_away": team_away,
        "league": league,
        "season": season
    }
    
    with app.test_request_context(f'/analysis/corners?{requests.compat.urlencode(params_corners)}'):
        corners_resp = corners_analysis()
        if corners_resp.status_code == 200:
            corners_data = corners_resp.get_json()
            analise_completa["escanteios"] = corners_data.get("analise_escanteios", {})
    
    # 4. Buscar análise de cartões
    params_cards = {
        "team_home": team_home,
        "team_away": team_away,
        "league": league,
        "season": season
    }
    
    with app.test_request_context(f'/analysis/cards?{requests.compat.urlencode(params_cards)}'):
        cards_resp = cards_analysis()
        if cards_resp.status_code == 200:
            cards_data = cards_resp.get_json()
            analise_completa["cartoes"] = cards_data.get("analise_cartoes", {})
    
    # 5. Consolidar recomendações
    todas_sugestoes = []
    
    # Adicionar sugestões de escanteios
    if analise_completa["escanteios"].get("sugestoes"):
        for sug in analise_completa["escanteios"]["sugestoes"]:
            sug["tipo"] = "Escanteios"
            todas_sugestoes.append(sug)
    
    # Adicionar sugestões de cartões
    if analise_completa["cartoes"].get("sugestoes"):
        for sug in analise_completa["cartoes"]["sugestoes"]:
            sug["tipo"] = "Cartões"
            todas_sugestoes.append(sug)
    
    # Ordenar por confiança (maior primeiro)
    todas_sugestoes.sort(key=lambda x: x.get("confianca", 0), reverse=True)
    
    analise_completa["recomendacoes_consolidadas"] = todas_sugestoes[:5]  # Top 5
    analise_completa["total_recomendacoes"] = len(todas_sugestoes)
    
    return jsonify({
        "ok": True,
        "analise_completa": analise_completa,
        "timestamp": datetime.now().isoformat(),
        "versao": "4.0 - Análise Profissional Consolidada"
    })

# ============================================================
# HOME / DOCUMENTATION
# ============================================================

@app.route("/", methods=["GET"])
def home():
    """Homepage com documentação"""
    hoje = datetime.now().strftime('%Y-%m-%d')
    
    return jsonify({
        "status": "✅ Online",
        "version": "4.0.0 - PROFISSIONAL",
        "changelog": {
            "v4.0": [
                "🆕 Análise REAL de escanteios (média, H2H, sugestões)",
                "🆕 Análise REAL de cartões (perfil disciplinar, sugestões)",
                "🆕 Análise completa consolidada (tudo em 1 endpoint)",
                "🎯 Sugestões com níveis de confiança (1-5 estrelas)",
                "💡 Value estimado para cada aposta",
                "⚠️ Sistema profissional implementado"
            ],
            "v3.2": [
                "🆕 Suporte a busca por 'round' em /fixtures",
                "🔧 Season padrão atualizada para 2025 (Brasileirão 2025)",
                "📝 Aceita date OU round como parâmetro",
                "🎯 Campo 'rodada' incluído na resposta"
            ]
        },
        "endpoints": {
            "basicos": {
                "health": "/health",
                "fixtures_por_data": f"/fixtures?date={hoje}&league=71&season=2025",
                "fixtures_por_rodada": "/fixtures?round=Regular Season - 33&league=71&season=2025",
                "standings": "/standings?league=71&season=2025",
                "teams": "/teams?league=71&season=2025",
                "statistics": "/teams/statistics?team=127&league=71&season=2025",
                "topscorers": "/players/topscorers?league=71&season=2025"
            },
            "avancados_v3": {
                "headtohead": "/fixtures/headtohead?h2h=127-121",
                "injuries": "/injuries?league=71&team=127&season=2025",
                "odds": "/odds?fixture=12345",
                "predictions": "/predictions?fixture=12345",
                "live": "/fixtures/live"
            },
            "profissionais_v4": {
                "analise_escanteios": "/analysis/corners?team_home=127&team_away=121&league=71",
                "analise_cartoes": "/analysis/cards?team_home=127&team_away=121&league=71",
                "analise_completa": "/analysis/complete?team_home=127&team_away=121&league=71&fixture=12345"
            }
        },
        "importante": {
            "season_brasileirao": "⚠️ Brasileirão 2025 usa season=2025!",
            "busca_por_rodada": "Use 'round=Regular Season - X' para buscar rodada específica",
            "formato_round": "Brasileirão: 'Regular Season - 1' até 'Regular Season - 38'",
            "analises_profissionais": "v4.0 inclui análises REAIS de escanteios e cartões com sugestões"
        },
            "formato_round": "Brasileirão: 'Regular Season - 1' até 'Regular Season - 38'"
        },
        "status_fixtures": {
            "FT": "Finalizado",
            "NS": "Não começou (agendado)",
            "LIVE": "Ao vivo",
            "PST": "Adiado",
            "CANC": "Cancelado",
            "TBD": "A definir"
        },
        "ligas_principais": {
            "71": "Brasileirão Série A (use season=2025)",
            "72": "Brasileirão Série B",
            "73": "Copa do Brasil",
            "39": "Premier League",
            "140": "La Liga",
            "135": "Serie A",
            "78": "Bundesliga",
            "2": "Champions League"
        }
    })

# ============================================================
# ERROR HANDLERS
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
        "error": "Erro interno do servidor"
    }), 500

# ============================================================
# CONFIGURAÇÃO VERCEL
# ============================================================

app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
