# 📋 Changelog — Apostas Esportivas Pro API

Todas as mudanças notáveis serão documentadas aqui.

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/),
seguindo [Semantic Versioning](https://semver.org/lang/pt-BR/).

---

## [6.1] - 2026-03-04

### Corrigido
- 🐛 **`/fixtures` agora retorna `mandante_id` e `visitante_id`** (URNs Sportradar dos times)
  - GPT pode obter os IDs diretamente sem chamada adicional
  - Protocolo de análise automática agora funcional end-to-end
- 🐛 **Instruções GPT corrigidas**: parâmetro `league` substituído por `competition` em todos os lugares
- 🐛 **IDs das ligas corrigidos**: IDs inteiros (API-Football) substituídos por URNs Sportradar
  - Antes: `league=39` → Agora: `competition=sr:competition:17`
  - Antes: `league=71` → Agora: `competition=sr:competition:325`

### Atualizado
- 📝 `openapi.yaml`: campos `mandante_id` e `visitante_id` adicionados ao schema de `/fixtures`
- 📝 `gpt-instructions-optimized.md`: tabela completa de URNs das 10 principais competições
- 📝 `gpt-instructions-chatgpt.md`: tabela completa de URNs e protocolo corrigido
- 📝 `README.md`: reescrito completamente para v6.1

---

## [6.0] - 2026-02-01

### 🎉 Major Release — Migração para Sportradar Soccer v4

### Mudado (Breaking)
- 🔄 **Migração completa de API-Sports v3 → Sportradar Soccer v4**
  - Novo formato de IDs: URNs como `sr:competition:325`, `sr:competitor:4783`
  - Novos endpoints Sportradar: `/schedules`, `/competitions`, `/competitors`
  - Taxa de chamadas: 1 req/s com retry automático (3x com backoff exponencial)

### Adicionado
- ✨ **`/analysis/complete`** — endpoint consolidado que substitui 7+ chamadas separadas
  - Retorna: contexto, stats, H2H, escanteios, cartões, lesões, previsões, Must Win
  - Auto-detecta temporada atual se `season` omitido
- ✨ **`/competitions`** — lista 22 competições suportadas com URNs Sportradar
- ✨ **`/seasons`** — temporadas disponíveis por competição
- ✨ **`/fixtures/live/analysis`** — análise ao vivo com Fator Must Win
- ✨ **`/fixtures/live/minute-by-minute`** — timeline de eventos do jogo ao vivo
- ✨ **Fator Must Win** — score 0-10 de pressão por resultado integrado em todas as análises
- ✨ **Auto-detecção de temporada** via `_get_current_season_urn()` (sem precisar informar)
- ✨ **`/news/context`** — notícias de GE.globo.com e ESPN.com.br por time/liga

### Deploy
- 🚀 Migrado de Vercel Serverless → Railway Container
  - Sem cold starts
  - Timeout ilimitado para chamadas longas
  - `nixpacks.toml` e `railway.json` adicionados
  - `Procfile` atualizado para gunicorn multi-worker

### Dependências
- ➕ `PyYAML==6.0.1` mantido para parsing do OpenAPI

---

## [5.1] - 2026-03-03

### Melhorado
- 🔐 Tratamento de erros de autenticação (HTTP 401/403) com mensagens claras
- 🩺 Health check `/health` com informações detalhadas da assinatura

### Corrigido
- 🐛 `/health` agora mostra status correto quando API_KEY expira, quota excedida ou assinatura vence

---

## [5.0] - 2025-11-13

### Adicionado
- ✨ Schema OpenAPI 3.1.0 completo (`openapi.yaml` + `/openapi.json`)
- ✨ Endpoint `/leagues` — lista 22 ligas suportadas
- 🩺 Health check avançado com teste de conectividade
- 📚 Docstrings completas em todas as funções

### Melhorado
- 🔒 Validações robustas de parâmetros com `validate_numeric_param()` e `validate_urn_param()`
- 📋 Constantes nomeadas (sem magic numbers): `DEFAULT_CORNERS_ESTIMATE`, `MAX_H2H_RESULTS`, etc.
- 📊 `/analysis/value` com interpretação, recomendação e fórmula exibida
- ⚡ Logging estruturado com timestamps
- 🔧 Validação de `API_KEY` na inicialização

---

## [4.2] - 2025-11-10

### Adicionado
- Suporte básico a parâmetros `timezone` e `status`

---

## [3.1.0] - 2024-11-06

### Adicionado
- ✨ Parâmetro `status` em `/fixtures`
- ✨ Parâmetro `timezone` em `/fixtures` (padrão: America/Sao_Paulo)

### Corrigido
- 🐛 Validação de `league_name` nas respostas

---

## [3.0.0] - 2024-10-15

### Adicionado
- ✨ `/fixtures/headtohead` (H2H)
- ✨ `/injuries` (lesões e suspensões)
- ✨ `/odds` (odds em tempo real)
- ✨ `/predictions` (previsões IA)
- ✨ `/fixtures/live` (jogos ao vivo)

---

## [2.0.0] - 2024-09-20

### Mudado
- 🔄 Migração de Render.com → Vercel
- 🔐 Variáveis de ambiente implementadas

---

## [1.0.0] - 2024-08-01

### Adicionado
- ✨ Release inicial: `/fixtures`, `/standings`, `/teams/statistics`
- ✨ Integração com API-Sports (substituída na v6.0)
- ✨ Deploy no Render.com

---

## Links

- [API em produção](https://apostasesportivaspro.up.railway.app)
- [OpenAPI Schema](https://apostasesportivaspro.up.railway.app/openapi.json)
- [GitHub](https://github.com/nlsoarez/apostasesportivaspro)
- [Sportradar Developer](https://developer.sportradar.com/)

---

**Desenvolvido com ⚽ para análise profissional de apostas esportivas**
