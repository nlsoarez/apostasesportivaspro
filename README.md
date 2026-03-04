# ⚽ Apostas Esportivas Pro — API v6.1

> Backend profissional de análise de apostas esportivas com IA (ChatGPT) e dados em tempo real

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.0.3-green.svg)](https://flask.palletsprojects.com/)
[![Sportradar](https://img.shields.io/badge/Sportradar-Soccer%20v4-orange.svg)](https://developer.sportradar.com/)
[![Railway](https://img.shields.io/badge/Deploy-Railway-purple.svg)](https://railway.app)

## 📋 Sobre o Projeto

**Apostas Esportivas Pro** é um backend Flask que fornece dados esportivos em tempo real via **Sportradar Soccer API v4** para um **Custom GPT** no ChatGPT. O GPT usa esses dados para análises profissionais de apostas — com classificação, H2H, lesões, odds, previsões, escanteios, cartões e o exclusivo **Fator Must Win**.

### ✨ Recursos Principais

- 🔄 **Dados em Tempo Real**: Sportradar Soccer API v4
- 🤖 **Custom GPT**: Integração nativa com ChatGPT via OpenAPI Actions
- 🎯 **Fator Must Win**: Score 0-10 de pressão por resultado (exclusivo)
- 📊 **22 Competições**: Brasil, Europa, Américas, Seleções
- ⚽ **Análise Completa**: 1 endpoint substitui 7+ chamadas separadas
- 💰 **Value Betting**: Cálculo automático de apostas com valor
- ⚡ **Jogos Ao Vivo**: Análise minuto a minuto com timeline
- 🔍 **Notícias**: Contexto de GE.globo.com e ESPN.com.br
- 🏥 **Lesões e Suspensões**: Dados atualizados por jogo
- 📈 **Artilheiros e Stats**: Estatísticas detalhadas por time

---

## 🚀 Tecnologias

| Componente | Tecnologia |
|---|---|
| Backend | Python 3.11+ + Flask 3.0.3 |
| Dados Esportivos | Sportradar Soccer API v4 |
| Deploy | Railway (Container) + Vercel (Serverless) |
| IA | ChatGPT Custom GPT (OpenAI) |
| Documentação | OpenAPI 3.1.0 |
| Rate Limiting | 1 req/s (Sportradar trial) |

---

## 📦 Instalação Local

### Pré-requisitos

- Python 3.11+
- Chave de API Sportradar (trial gratuito em [developer.sportradar.com](https://developer.sportradar.com))

### Setup

```bash
# Clone o repositório
git clone https://github.com/nlsoarez/apostasesportivaspro.git
cd apostasesportivaspro

# Instale as dependências
pip install -r requirements.txt

# Configure a variável de ambiente
echo "API_KEY=sua_chave_sportradar_aqui" > .env

# Execute o servidor
python main.py
```

Servidor disponível em `http://localhost:8080`

---

## 🌐 Deploy

### Railway (Recomendado)

1. Conecte o repositório no [Railway](https://railway.app)
2. Configure a variável de ambiente: `API_KEY=sua_chave_sportradar`
3. Deploy automático via Nixpacks ✅

### Vercel (Serverless)

1. Importe o projeto no [Vercel](https://vercel.com)
2. Configure: `API_KEY=sua_chave_sportradar`
3. O arquivo `vercel.json` e `api/index.py` já estão configurados ✅

---

## 📡 Endpoints da API

> **Importante:** Todos os IDs usam formato URN Sportradar — ex: `sr:competition:325`, `sr:competitor:4783`.
> Use `/competitions` para listar todas as competições com seus URNs.

### Infraestrutura

| Endpoint | Descrição |
|---|---|
| `GET /` | Documentação e status da API |
| `GET /health` | Health check com teste de conectividade |
| `GET /openapi.json` | Schema OpenAPI 3.1.0 completo |

### Competições e Temporadas

| Endpoint | Parâmetros | Descrição |
|---|---|---|
| `GET /competitions` | — | Lista 22 competições com URNs |
| `GET /leagues` | — | Alias de `/competitions` |
| `GET /seasons` | `competition` (URN) | Temporadas de uma competição |

### Fixtures e Jogos

| Endpoint | Parâmetros | Descrição |
|---|---|---|
| `GET /fixtures` | `date` (YYYY-MM-DD), `competition` (URN, opcional) | Jogos por data — inclui `mandante_id` e `visitante_id` |
| `GET /fixtures/headtohead` | `team1` (URN), `team2` (URN) | H2H: histórico + próximos jogos |
| `GET /fixtures/live` | — | Todos os jogos ao vivo agora |
| `GET /fixtures/live/analysis` | `fixture` (URN) | Análise completa ao vivo |
| `GET /fixtures/live/minute-by-minute` | `fixture` (URN) | Timeline minuto a minuto |

### Dados por Competição

| Endpoint | Parâmetros | Descrição |
|---|---|---|
| `GET /standings` | `competition` (URN), `season` (URN, opcional) | Classificação — inclui `time_id` de cada time |
| `GET /teams/statistics` | `team` (URN), `competition` (URN), `season` (URN, opcional) | Estatísticas do time |
| `GET /players/topscorers` | `competition` (URN), `season` (URN, opcional) | Artilheiros |
| `GET /injuries` | `competition` (URN) ou `team` (URN), `season` (URN, opcional) | Lesões e suspensões |

### Previsões e Apostas

| Endpoint | Parâmetros | Descrição |
|---|---|---|
| `GET /predictions` | `fixture` (URN) | Previsões IA |
| `GET /odds` | `fixture` (URN) | Odds dos bookmakers |
| `GET /analysis/value` | `odd`, `probability` | Cálculo de value betting |

### Análises com Fator Must Win

| Endpoint | Parâmetros | Descrição |
|---|---|---|
| `GET /analysis/corners` | `team_home` (URN), `team_away` (URN), `competition` (URN) | Análise de escanteios |
| `GET /analysis/cards` | `team_home` (URN), `team_away` (URN), `competition` (URN) | Análise de cartões |
| `GET /analysis/complete` | `team_home` (URN), `team_away` (URN), `competition` (URN), `fixture` (URN, opcional) | **Análise completa** — substitui 7+ chamadas |

### Notícias

| Endpoint | Parâmetros | Descrição |
|---|---|---|
| `GET /news/context` | `team`, `league`, `days` (1-30, padrão 3) | Notícias recentes (GE.globo + ESPN) |

---

## 🏆 Competições Suportadas

### Brasil
| Competição | URN |
|---|---|
| Brasileirão Série A | `sr:competition:325` |
| Brasileirão Série B | `sr:competition:390` |
| Copa do Brasil | `sr:competition:531` |
| Campeonato Carioca | `sr:competition:621` |
| Campeonato Paulista | `sr:competition:624` |

### Europa
| Competição | URN |
|---|---|
| Premier League | `sr:competition:17` |
| La Liga | `sr:competition:8` |
| Serie A (Itália) | `sr:competition:23` |
| Bundesliga | `sr:competition:35` |
| Ligue 1 | `sr:competition:34` |
| Primeira Liga | `sr:competition:238` |
| Eredivisie | `sr:competition:37` |

### Internacional
| Competição | URN |
|---|---|
| UEFA Champions League | `sr:competition:7` |
| UEFA Europa League | `sr:competition:679` |
| UEFA Conference League | `sr:competition:929` |
| Copa Libertadores | `sr:competition:384` |
| Copa Sul-Americana | `sr:competition:480` |

### Américas e Seleções
| Competição | URN |
|---|---|
| MLS | `sr:competition:242` |
| Liga MX | `sr:competition:316` |
| Copa do Mundo FIFA | `sr:competition:1` |
| Eurocopa | `sr:competition:9` |
| Copa América | `sr:competition:133` |

---

## 🎯 Fator Must Win

O **Must Win Score** (0-10) mede a pressão por resultado de um time, integrado automaticamente nas análises de escanteios, cartões e ao vivo.

| Score | Nível | Descrição |
|---|---|---|
| 8-10 | CRÍTICO | Pressão extrema (rebaixamento, sequência péssima) |
| 6.5-8 | ALTO | Precisa pontuar urgentemente |
| 5-6.5 | MODERADO | Jogo importante, mas sem desespero |
| 0-5 | BAIXO | Situação confortável |

**Exemplo de uso:**
```bash
# Análise completa com Must Win integrado
curl "https://apostasesportivaspro.up.railway.app/analysis/complete\
?team_home=sr:competitor:4783\
&team_away=sr:competitor:4785\
&competition=sr:competition:325"
```

---

## 🤖 Integração com ChatGPT

Este projeto foi projetado para ser usado como **Custom GPT Action**.

### Como configurar

1. Crie um Custom GPT em [chat.openai.com](https://chat.openai.com)
2. Nas Actions, importe o schema via URL:
   ```
   https://apostasesportivaspro.up.railway.app/openapi.json
   ```
3. Adicione as instruções do arquivo `gpt-instructions-optimized.md` como System Prompt
4. Pronto! O GPT busca dados reais automaticamente ✅

### Fluxo automático do GPT

Quando o usuário envia uma lista de jogos, o GPT executa automaticamente:

1. `GET /fixtures?date=YYYY-MM-DD` → obtém `mandante_id`, `visitante_id`, `competicao_id`
2. `GET /analysis/complete?team_home=...&team_away=...&competition=...` → análise completa
3. Apresenta análise com Must Win Score integrado

---

## 💡 Exemplos de Uso

```bash
# Jogos de hoje no Brasileirão
curl "https://apostasesportivaspro.up.railway.app/fixtures\
?date=2026-03-04&competition=sr:competition:325"

# Classificação Premier League (temporada detectada automaticamente)
curl "https://apostasesportivaspro.up.railway.app/standings\
?competition=sr:competition:17"

# Análise completa de jogo
curl "https://apostasesportivaspro.up.railway.app/analysis/complete\
?team_home=sr:competitor:4783\
&team_away=sr:competitor:4785\
&competition=sr:competition:325"

# Value Bet: odd 2.5 com probabilidade 45%
curl "https://apostasesportivaspro.up.railway.app/analysis/value\
?odd=2.5&probability=0.45"

# Notícias recentes sobre o Flamengo
curl "https://apostasesportivaspro.up.railway.app/news/context\
?team=Flamengo&league=Brasileirao&days=5"
```

---

## 🗂️ Estrutura do Projeto

```
apostasesportivaspro/
├── main.py                          # API Flask principal (22 endpoints)
├── openapi.yaml                     # Schema OpenAPI 3.1.0
├── requirements.txt                 # Dependências Python
├── Procfile                         # Gunicorn (Railway/Heroku)
├── nixpacks.toml                    # Build Railway
├── railway.json                     # Deploy Railway
├── vercel.json                      # Deploy Vercel
├── runtime.txt                      # Python 3.11.x
├── api/
│   └── index.py                     # Entry point Vercel serverless
├── gpt-instructions-optimized.md   # System prompt do GPT (completo)
├── gpt-instructions-chatgpt.md     # System prompt do GPT (condensado)
├── CHANGELOG.md                     # Histórico de versões
└── .gitignore
```

---

## ⚠️ Jogo Responsável

Este sistema é para **análise e educação**, não garante resultados.

- 🎯 Use apenas para decisões informadas
- 💰 Nunca aposte mais do que pode perder
- 📈 Estabeleça e respeite limites de banca
- 🚫 Se o jogo deixar de ser diversão, procure ajuda

**Recursos:**
- [Jogadores Anônimos Brasil](https://www.jogadoresanonimos.com.br/)
- Ligue 141 (CVV — apoio emocional)

---

## 👤 Autor

**Nelson Soares**
- GitHub: [@nlsoarez](https://github.com/nlsoarez)

## 🔗 Links

- [API em produção](https://apostasesportivaspro.up.railway.app)
- [Schema OpenAPI](https://apostasesportivaspro.up.railway.app/openapi.json)
- [Sportradar Developer](https://developer.sportradar.com/)
- [Flask Docs](https://flask.palletsprojects.com/)

---

**Desenvolvido com ⚽ para análise profissional de apostas esportivas**
