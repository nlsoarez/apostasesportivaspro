import requests
from bs4 import BeautifulSoup
from datetime import datetime

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/119.0 Safari/537.36"
}

# ==============================================================
# 📅 1️⃣ Jogos do dia (ESPN Brasil)
# ==============================================================
def get_fixtures_backup():
    try:
        url = "https://www.espn.com.br/futebol/agenda"
        html = requests.get(url, headers=HEADERS, timeout=15).text
        soup = BeautifulSoup(html, "html.parser")

        jogos = []
        for bloco in soup.select("section.Schedule__Card"):
            horario = bloco.select_one(".Schedule__Time")
            times = bloco.select(".Schedule__Team")

            if horario and len(times) == 2:
                jogos.append({
                    "hora": horario.text.strip(),
                    "mandante": times[0].text.strip(),
                    "visitante": times[1].text.strip()
                })

        return {
            "fonte": "ESPN Brasil",
            "atualizado": datetime.now().isoformat(),
            "total": len(jogos),
            "jogos": jogos
        }

    except Exception as e:
        return {"erro": str(e), "fonte": "ESPN Brasil"}


# ==============================================================
# 🏆 2️⃣ Classificação do Brasileirão (GE.globo)
# ==============================================================
def get_standings_backup():
    try:
        url = "https://ge.globo.com/futebol/brasileirao-serie-a/"
        html = requests.get(url, headers=HEADERS, timeout=15).text
        soup = BeautifulSoup(html, "html.parser")

        tabela = []
        for linha in soup.select("table tbody tr"):
            pos = linha.select_one(".classificacao__posicao")
            time = linha.select_one(".classificacao__equipes .classificacao__equipes--nome")
            pontos = linha.select_one(".classificacao__pontos")

            if pos and time and pontos:
                tabela.append({
                    "posicao": pos.text.strip(),
                    "time": time.text.strip(),
                    "pontos": pontos.text.strip()
                })

        return {
            "fonte": "Globo Esporte",
            "atualizado": datetime.now().isoformat(),
            "total": len(tabela),
            "tabela": tabela
        }

    except Exception as e:
        return {"erro": str(e), "fonte": "Globo Esporte"}


# ==============================================================
# ⚽ 3️⃣ Artilheiros (OGol)
# ==============================================================
def get_topscorers_backup():
    try:
        url = "https://www.ogol.com.br/edition.php?id_edicao=180067"
        html = requests.get(url, headers=HEADERS, timeout=15).text
        soup = BeautifulSoup(html, "html.parser")

        jogadores = []
        for linha in soup.select("table tr")[1:]:
            colunas = [c.text.strip() for c in linha.select("td")]
            if len(colunas) >= 4:
                jogadores.append({
                    "jogador": colunas[1],
                    "time": colunas[2],
                    "gols": colunas[3]
                })

        return {
            "fonte": "OGol",
            "atualizado": datetime.now().isoformat(),
            "total": len(jogadores),
            "artilheiros": jogadores
        }

    except Exception as e:
        return {"erro": str(e), "fonte": "OGol"}
