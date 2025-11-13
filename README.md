# ⚽ GPT Apostas Futebol Pro

> Sistema profissional de análise de apostas esportivas com IA e dados em tempo real

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.0.3-green.svg)](https://flask.palletsprojects.com/)
[![API-Sports](https://img.shields.io/badge/API--Sports-v3-orange.svg)](https://api-sports.io/)
[![Vercel](https://img.shields.io/badge/Deploy-Vercel-black.svg)](https://vercel.com)

## 📋 Sobre o Projeto

**GPT Apostas Futebol Pro** é um sistema avançado que combina inteligência artificial (ChatGPT) com dados esportivos em tempo real da API-Sports para fornecer análises profissionais de apostas em futebol.

### ✨ Recursos Principais

- 🔄 **Dados em Tempo Real**: Integração direta com API-Sports
- 🤖 **Análise por IA**: Powered by ChatGPT para insights profundos
- 📊 **50+ Ligas**: Cobertura global incluindo Brasileirão, Champions League, e principais ligas europeias
- 📈 **Estatísticas Avançadas**: H2H, lesões, odds reais, previsões IA
- 💰 **Value Betting**: Identificação automática de apostas com valor
- 🎯 **Kelly Criterion**: Gestão profissional de banca
- ⚡ **Jogos Ao Vivo**: Monitoramento de partidas em andamento

## 🚀 Tecnologias

- **Backend**: Python 3.11+ com Flask
- **API de Dados**: API-Sports v3 (api-football)
- **Deploy**: Vercel (Serverless Functions)
- **IA**: ChatGPT (OpenAI)
- **Segurança**: Variáveis de ambiente, CORS configurado

## 📦 Instalação

### Pré-requisitos

- Python 3.11 ou superior
- Conta na [API-Sports](https://api-sports.io/) (Free tier disponível)
- Conta no [Vercel](https://vercel.com) (opcional, para deploy)

### Instalação Local

```bash
# Clone o repositório
git clone https://github.com/nlsoarez/apostasesportivaspro.git
cd apostasesportivaspro

# Instale as dependências
pip install -r requirements.txt

# Configure as variáveis de ambiente
# Crie um arquivo .env na raiz do projeto:
API_KEY=sua_chave_api_sports_aqui
API_HOST=v3.football.api-sports.io

# Execute o servidor
python main.py
```

O servidor estará disponível em `http://localhost:8080`

## 🌐 Deploy na Vercel

1. Faça fork/clone deste repositório
2. Importe o projeto no [Vercel](https://vercel.com)
3. Configure as variáveis de ambiente:
   - `API_KEY`: Sua chave da API-Sports
   - `API_HOST`: `v3.football.api-sports.io`
4. Deploy automático! ✅

## 📡 Endpoints da API

### Endpoints Básicos

| Endpoint | Descrição | Parâmetros |
|----------|-----------|------------|
| `GET /health` | Status da API | - |
| `GET /` | Documentação completa | - |
| `GET /fixtures` | Jogos por data/liga | `date`, `league`, `season`, `status`, `timezone` |
| `GET /standings` | Classificação | `league`, `season` |
| `GET /teams` | Times da liga | `league`, `season` |
| `GET /teams/statistics` | Stats de um time | `team`, `league`, `season` |
| `GET /players/topscorers` | Artilheiros | `league`, `season` |

### Endpoints Avançados v3.0 🆕

| Endpoint | Descrição | Parâmetros |
|----------|-----------|------------|
| `GET /fixtures/headtohead` | Confronto direto (H2H) | `h2h` (ex: `127-121`) |
| `GET /injuries` | Lesões e suspensões | `league`, `team`, `season` |
| `GET /odds` | Odds em tempo real | `fixture` (id do jogo) |
| `GET /predictions` | Previsões IA | `fixture` (id do jogo) |
| `GET /fixtures/live` | Jogos ao vivo | - |

### Exemplos de Uso

```bash
# Buscar jogos do Brasileirão de hoje
curl "https://seu-dominio.vercel.app/fixtures?date=2024-11-06&league=71&season=2024"

# Classificação do Brasileirão
curl "https://seu-dominio.vercel.app/standings?league=71&season=2024"

# Confronto direto Flamengo vs Palmeiras
curl "https://seu-dominio.vercel.app/fixtures/headtohead?h2h=127-121"

# Lesões do Flamengo
curl "https://seu-dominio.vercel.app/injuries?league=71&team=127&season=2024"

# Jogos ao vivo agora
curl "https://seu-dominio.vercel.app/fixtures/live"
```

## 🏆 Ligas Suportadas

### Brasil
- **71** - Brasileirão Série A
- **72** - Brasileirão Série B
- **73** - Copa do Brasil
- **75** - Campeonato Carioca
- **76** - Campeonato Paulista

### Europa
- **39** - Premier League (Inglaterra)
- **140** - La Liga (Espanha)
- **135** - Serie A (Itália)
- **78** - Bundesliga (Alemanha)
- **61** - Ligue 1 (França)

### Competições Internacionais
- **2** - UEFA Champions League
- **3** - UEFA Europa League
- **13** - Copa Libertadores
- **11** - Copa Sul-Americana

[Ver lista completa de 50+ ligas no código]

## 🤖 Integração com ChatGPT

Este backend foi projetado para ser usado como **Custom GPT Action**. O GPT utiliza os endpoints para:

1. Buscar dados em tempo real
2. Analisar estatísticas e históricos
3. Calcular probabilidades e value betting
4. Considerar lesões e contexto atual
5. Comparar com previsões IA da API-Sports
6. Fornecer recomendações profissionais

### Como Configurar o GPT

1. Crie um Custom GPT no ChatGPT
2. Adicione o arquivo `CONHECIMENTO_V6_ATUALIZADO.docx` como Knowledge Base
3. Configure as Actions apontando para sua API Vercel
4. Use o schema OpenAPI 3.0.0 (incluído na raiz `/`)

## 📊 Formato de Análise

O sistema gera análises estruturadas incluindo:

- ✅ Contexto atual dos times (posição, forma, estatísticas)
- ✅ Histórico de confrontos diretos (H2H)
- ✅ Situação do elenco (lesões e suspensões)
- ✅ Análise estatística profunda
- ✅ Odds reais de bookmakers
- ✅ Validação por IA (API-Sports predictions)
- ✅ Cálculo de value betting
- ✅ Gestão de banca (Kelly Criterion)
- ✅ Níveis de confiança e stakes recomendados
- ✅ Transparência sobre riscos

## ⚠️ Jogo Responsável

Este sistema é para **análise e educação**, não garante resultados.

**Diretrizes:**
- 🎯 Use apenas para decisões informadas
- 💰 Nunca aposte mais do que pode perder
- 📈 Estabeleça e respeite limites
- 🚫 Se o jogo deixar de ser diversão, procure ajuda

**Recursos de Ajuda:**
- [Jogadores Anônimos Brasil](https://www.jogadoresanonimos.com.br/)
- Ligue 141 (CVV - Apoio emocional)

## 🔧 Estrutura do Projeto

```
apostasesportivaspro/
├── main.py                          # API Flask principal
├── requirements.txt                 # Dependências Python
├── vercel.json                      # Configuração Vercel
├── .gitignore                       # Arquivos ignorados
├── README.md                        # Este arquivo
└── CONHECIMENTO_V6_ATUALIZADO.docx  # Knowledge base do GPT
```

## 📈 Changelog

### v5.0 (Atual) 🎉
- ✨ **Schema OpenAPI 3.1.0 completo** (`/openapi.json`)
- ✨ **Endpoint `/leagues`** - Lista todas as ligas suportadas
- 🔒 **Validações robustas** de parâmetros com ranges e tipos
- 📋 **Constantes configuráveis** (sem magic numbers)
- 📚 **Docstrings completas** em todas as funções
- 🩺 **Health check avançado** com teste de conectividade
- 🎯 **Mensagens de erro detalhadas** com exemplos
- ⚡ **Logging estruturado** com timestamps
- 🔧 **Validação de API_KEY** na inicialização
- 📊 **Value Bet melhorado** com interpretação e fórmula
- 🌍 **22 ligas categorizadas** (Brasil, Europa, Internacional)
- 🐛 Correções de bugs e melhorias de performance

### v3.1.0
- ✨ Parâmetro `status` em `/fixtures` (FT, NS, LIVE, etc.)
- ✨ Parâmetro `timezone` em `/fixtures` (padrão: America/Sao_Paulo)
- 🐛 Validação de `league_name` nas respostas
- 💬 Mensagens de erro melhoradas
- 🎯 Tratamento para "nenhum jogo encontrado"

### v3.0.0
- ✨ Endpoint `/fixtures/headtohead` (H2H)
- ✨ Endpoint `/injuries` (lesões e suspensões)
- ✨ Endpoint `/odds` (odds em tempo real)
- ✨ Endpoint `/predictions` (previsões IA)
- ✨ Endpoint `/fixtures/live` (jogos ao vivo)
- 📊 Análises 3x mais completas

### v2.0.0
- 🔄 Migração de Render.com para Vercel
- 🔐 Implementação de variáveis de ambiente
- 🌐 Correção de autenticação API-Sports
- 📝 Documentação completa

## 🤝 Contribuindo

Contribuições são bem-vindas! Para contribuir:

1. Fork o projeto
2. Crie uma branch para sua feature (`git checkout -b feature/AmazingFeature`)
3. Commit suas mudanças (`git commit -m 'Add some AmazingFeature'`)
4. Push para a branch (`git push origin feature/AmazingFeature`)
5. Abra um Pull Request

## 📝 Licença

Este projeto é de código aberto para fins educacionais.

**Importante**: O uso comercial requer:
- Assinatura paga da API-Sports
- Conformidade com regulamentações locais de apostas
- Licenças apropriadas

## 👤 Autor

**Nelson Soares**
- GitHub: [@nlsoarez](https://github.com/nlsoarez)
- Projeto: [apostasesportivaspro](https://github.com/nlsoarez/apostasesportivaspro)

## 🔗 Links Úteis

- [API-Sports Documentação](https://www.api-football.com/documentation-v3)
- [Flask Documentação](https://flask.palletsprojects.com/)
- [Vercel Documentação](https://vercel.com/docs)
- [OpenAI Custom GPTs](https://platform.openai.com/docs/guides/gpt)

## 💬 Suporte

Encontrou um bug ou tem uma sugestão?

1. Verifique se já existe uma [issue](https://github.com/nlsoarez/apostasesportivaspro/issues)
2. Se não, crie uma nova issue com detalhes
3. Para dúvidas, use as [Discussions](https://github.com/nlsoarez/apostasesportivaspro/discussions)

---

⭐ Se este projeto foi útil, considere dar uma estrela no GitHub!

**Desenvolvido com ⚽ para análise profissional de apostas esportivas**
