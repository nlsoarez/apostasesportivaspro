# 📋 Changelog - Apostas Esportivas Pro API

Todas as mudanças notáveis neste projeto serão documentadas neste arquivo.

O formato é baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/),
e este projeto adere ao [Semantic Versioning](https://semver.org/lang/pt-BR/).

---

## [5.1] - 2026-03-03

### Melhorado
- 🔐 **Tratamento de erros de autenticação na API-Sports**
  - HTTP 401: Mensagem clara indicando chave inválida ou expirada com link para renovação
  - HTTP 403: Mensagem indicando sem permissão no plano atual
  - Antes retornava apenas "Erro HTTP 401/403" sem orientação

- 🩺 **Health check `/health` aprimorado com informações da assinatura**
  - Plano atual (Free, Pro, etc.)
  - Status da assinatura (ativa ou expirada)
  - Data de vencimento da assinatura
  - Quota diária: requisições usadas, limite e percentual
  - Email da conta associada
  - Campo `action` com instrução de resolução quando há problemas

### Corrigido
- 🐛 Quando API_KEY expira, `/health` agora mostra `"api_sports_status": "invalid_key"` com ação de correção
- 🐛 Quando quota diária é atingida, mostra `"api_sports_status": "quota_exceeded"`
- 🐛 Quando assinatura vence, mostra `"api_sports_status": "subscription_expired"`

---

## [5.0] - 2025-11-13

### 🎉 Major Release - Melhorias de Qualidade e Documentação

### Adicionado
- ✨ **Schema OpenAPI 3.1.0 completo** (`openapi.yaml` e endpoint `/openapi.json`)
  - Documentação completa de todos os 14 endpoints
  - Exemplos de requisição e resposta
  - Parâmetros com validações e constraints
  - Componentes reutilizáveis

- ✨ **Novo endpoint `/leagues`**
  - Lista todas as 22 ligas suportadas
  - Categorização por região (Brasil, Europa, Internacional, etc.)
  - Total de ligas e IDs organizados

- 🩺 **Health check avançado** em `/health`
  - Timestamp da requisição
  - Teste de conectividade com API-Sports
  - Status detalhado da API externa
  - Versão da API

- 📚 **Docstrings completas**
  - Todas as funções documentadas
  - Descrição de parâmetros e retornos
  - Exemplos de uso

### Melhorado
- 🔒 **Validações robustas de parâmetros**
  - Funções auxiliares: `validate_numeric_param()` e `validate_integer_param()`
  - Validação de ranges (odds: 1.01-100.0, probability: 0.01-1.0)
  - Mensagens de erro com exemplos práticos
  - Tratamento específico por tipo de dado

- 📋 **Constantes configuráveis**
  - `API_VERSION = "5.0"`
  - `DEFAULT_SEASON = 2025`
  - `DEFAULT_TIMEZONE = "America/Sao_Paulo"`
  - `DEFAULT_NEWS_DAYS = 3`
  - `MAX_NEWS_DAYS = 30`
  - `MAX_LIVE_FIXTURES = 20`
  - `MAX_H2H_RESULTS = 10`
  - `DEFAULT_CORNERS_ESTIMATE = 10.0`
  - `DEFAULT_CARDS_ESTIMATE = 5.5`
  - Eliminação de "magic numbers" no código

- 📊 **Endpoint `/analysis/value` melhorado**
  - Validação rigorosa de odd e probability
  - Interpretação do resultado (Value Bet ✅ ou Sem Value ❌)
  - Recomendação (Apostar ou Evitar)
  - Fórmula exibida na resposta

- ⚡ **Logging estruturado**
  - Formato padronizado com timestamp
  - Níveis apropriados (INFO, WARNING, ERROR)
  - Contexto detalhado nos erros

- 🔧 **Validação de API_KEY na inicialização**
  - Aviso crítico se API_KEY não estiver configurada
  - Falha rápida com mensagem clara

- 🌍 **Dicionário de ligas suportadas**
  - 22 ligas organizadas por região
  - Brasil: 5 ligas (Brasileirão A/B, Copa do Brasil, Carioca, Paulista)
  - Europa: 7 ligas (Premier League, La Liga, Serie A, Bundesliga, Ligue 1, Primeira Liga, Eredivisie)
  - Internacional: 5 competições (Champions, Europa, Conference League, Libertadores, Sul-Americana)
  - Américas: 2 ligas (MLS, Liga MX)
  - Mundial: 2 torneios (Copa do Mundo, Eurocopa)

### Corrigido
- 🐛 Magic numbers substituídos por constantes nomeadas
- 🐛 Tratamento de exceções melhorado em `/analysis/corners` e `/analysis/cards`
- 🐛 Validação de formato h2h em `/fixtures/headtohead`
- 🐛 Validação de range de days em `/news/context` (1-30)
- 🐛 Mensagens de erro mais descritivas em todos os endpoints

### Dependências
- ➕ Adicionado: `PyYAML==6.0.1` (para parsing do OpenAPI)

### Documentação
- 📝 README atualizado com changelog da v5.0
- 📝 Novo arquivo `CHANGELOG.md` criado
- 📝 Schema OpenAPI publicado e acessível via API

### Endpoints Atualizados
Todos os endpoints receberam melhorias:
1. `GET /` - Informações da API com link para documentação
2. `GET /health` - Health check avançado
3. `GET /openapi.json` - Schema OpenAPI completo
4. `GET /leagues` - Lista de ligas suportadas (NOVO)
5. `GET /fixtures` - Validações melhoradas
6. `GET /fixtures/headtohead` - Validação de formato
7. `GET /fixtures/live` - Inclui placar dos jogos
8. `GET /standings` - Validações de parâmetros
9. `GET /teams/statistics` - Código limpo
10. `GET /players/topscorers` - Código limpo
11. `GET /injuries` - Código limpo
12. `GET /odds` - Código limpo
13. `GET /predictions` - Código limpo
14. `GET /analysis/corners` - Validações e constantes
15. `GET /analysis/cards` - Validações e constantes
16. `GET /analysis/value` - Melhorias significativas
17. `GET /news/context` - Validação de range e constantes

---

## [4.2] - 2025-11-10

### Adicionado
- Suporte básico a parâmetros timezone e status

---

## [3.1.0] - 2024-11-06

### Adicionado
- ✨ Parâmetro `status` em `/fixtures` (FT, NS, LIVE, etc.)
- ✨ Parâmetro `timezone` em `/fixtures` (padrão: America/Sao_Paulo)

### Melhorado
- 💬 Mensagens de erro melhoradas
- 🎯 Tratamento para "nenhum jogo encontrado"

### Corrigido
- 🐛 Validação de `league_name` nas respostas

---

## [3.0.0] - 2024-10-15

### 🎉 Major Release - Endpoints Avançados

### Adicionado
- ✨ Endpoint `/fixtures/headtohead` (H2H - Confronto direto)
- ✨ Endpoint `/injuries` (Lesões e suspensões)
- ✨ Endpoint `/odds` (Odds em tempo real)
- ✨ Endpoint `/predictions` (Previsões IA da API-Sports)
- ✨ Endpoint `/fixtures/live` (Jogos ao vivo)

### Melhorado
- 📊 Análises 3x mais completas com dados contextuais

---

## [2.0.0] - 2024-09-20

### 🎉 Major Release - Deploy e Infraestrutura

### Adicionado
- 🔐 Suporte a variáveis de ambiente (.env)
- 📝 Documentação completa no README

### Mudado
- 🔄 Migração de Render.com para Vercel
- 🌐 Autenticação API-Sports corrigida

---

## [1.0.0] - 2024-08-01

### 🎉 Release Inicial

### Adicionado
- ✨ Endpoints básicos: `/fixtures`, `/standings`, `/teams/statistics`
- ✨ Integração com API-Sports
- ✨ Deploy inicial no Render.com
- ✨ Suporte a múltiplas ligas

---

## Links Úteis

- [API Documentation](https://apostasesportivas.vercel.app/)
- [OpenAPI Schema](https://apostasesportivas.vercel.app/openapi.json)
- [GitHub Repository](https://github.com/nlsoarez/apostasesportivaspro)
- [API-Sports](https://api-sports.io/)

---

**Desenvolvido com ⚽ para análise profissional de apostas esportivas**
