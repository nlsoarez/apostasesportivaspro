# 🎯 GPT Apostas Futebol Pro

[![Python](https://img.shields.io/badge/Python-3.13-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.0.3-green.svg)](https://flask.palletsprojects.com/)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Sistema inteligente de análise e previsão para apostas esportivas em futebol, combinando dados estatísticos em tempo real com inteligência artificial.

## 📋 Índice

- [Recursos](#-recursos)
- [Arquitetura](#-arquitetura)
- [Instalação](#-instalação)
- [Configuração](#-configuração)
- [Uso](#-uso)
- [API Endpoints](#-api-endpoints)
- [Deploy](#-deploy)
- [Contribuindo](#-contribuindo)

## ✨ Recursos

### Core Features
- ⚽ **Dados em Tempo Real** - Integração com API-Football para estatísticas ao vivo
- 🤖 **Análise com IA** - Previsões baseadas em machine learning
- 📊 **Value Betting** - Identificação automática de apostas de valor
- 💰 **Gestão de Banca** - Sistema Kelly Criterion para otimização de stakes
- 🔄 **Multi-fonte** - Fallback automático com web scraping
- 📈 **Dashboard** - Interface web com visualizações interativas

### Análises Disponíveis
- Probabilidades de vitória/empate/derrota
- Over/Under de gols
- Both Teams to Score (BTTS)
- Handicap Asiático
- Confronto direto (H2H)
- Forma recente e estatísticas

## 🏗 Arquitetura

```
┌─────────────────────────────────────────────────────┐
│                   Frontend (Widget)                  │
└────────────────────────┬────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────┐
│                    Nginx (Proxy)                     │
└────────────────────────┬────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────┐
│                  Flask API (Python)                  │
├─────────────────────────────────────────────────────┤
│  • Endpoints REST                                    │
│  • Cache Manager                                     │
│  • Análise Estatística                              │
│  • Sistema de Fallback                              │
└────────┬───────────────────────────┬────────────────┘
         │                           │
    ┌────▼────┐              ┌──────▼──────┐
    │  Redis  │              │ API-Football │
    │ (Cache) │              │   (Dados)   │
    └─────────┘              └──────┬──────┘
                                    │
                             ┌──────▼──────┐
                             │ Web Scraping│
                             │  (Backup)   │
                             └─────────────┘
```

## 🚀 Instalação

### Requisitos
- Python 3.13+
- Redis (opcional, para cache)
- Docker & Docker Compose (para deploy completo)

### Instalação Local

```bash
# Clone o repositório
git clone https://github.com/seu-usuario/gpt-apostas-futebol-pro.git
cd gpt-apostas-futebol-pro

# Crie um ambiente virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows

# Instale as dependências
pip install -r requirements.txt

# Configure as variáveis de ambiente
cp .env.example .env
# Edite o arquivo .env com suas credenciais
```

### Instalação com Docker

```bash
# Clone o repositório
git clone https://github.com/seu-usuario/gpt-apostas-futebol-pro.git
cd gpt-apostas-futebol-pro

# Configure as variáveis de ambiente
cp .env.example .env
# Edite o arquivo .env

# Inicie todos os serviços
docker-compose up -d
```

## ⚙️ Configuração

### Variáveis de Ambiente

Crie um arquivo `.env` na raiz do projeto:

```env
# API-Football (RapidAPI)
API_KEY=sua_chave_rapidapi_aqui
API_HOST=api-football-v1.p.rapidapi.com

# Flask
FLASK_ENV=development
FLASK_DEBUG=True
SECRET_KEY=sua_chave_secreta_aqui

# Redis (opcional)
REDIS_URL=redis://localhost:6379/0

# Banco de Dados (opcional)
DATABASE_URL=postgresql://user:pass@localhost/dbname

# Monitoring (Grafana)
GRAFANA_USER=admin
GRAFANA_PASSWORD=senha_segura_aqui
```

### Obter API Key

1. Acesse [RapidAPI](https://rapidapi.com/api-sports/api/api-football)
2. Crie uma conta gratuita
3. Inscreva-se na API-Football
4. Copie sua API Key
5. Cole no arquivo `.env`

## 📖 Uso

### Executar o Servidor

```bash
# Desenvolvimento
python main.py

# Produção
gunicorn main:app --bind 0.0.0.0:8080 --workers 4
```

### Acessar a Aplicação

- **API**: http://localhost:8080
- **Widget**: http://localhost:8080/app
- **Docs**: http://localhost:8080/docs
- **Grafana**: http://localhost:3000 (com Docker)
- **Flower**: http://localhost:5555 (com Docker)

### Exemplo de Uso com Python

```python
import requests
from datetime import datetime

# Configuração
BASE_URL = "http://localhost:8080"
LEAGUE_ID = "71"  # Brasileirão Série A

# Buscar jogos de hoje
today = datetime.now().strftime("%Y-%m-%d")
response = requests.get(f"{BASE_URL}/fixtures", params={
    "date": today,
    "league": LEAGUE_ID
})

jogos = response.json()
print(f"Jogos encontrados: {len(jogos['data']['response'])}")

# Analisar uma partida específica
fixture_id = jogos['data']['response'][0]['fixture']['id']
analysis = requests.post(f"{BASE_URL}/analyze", json={
    "fixture_id": fixture_id,
    "include_odds": True,
    "include_predictions": True
})

print(analysis.json())
```

## 🔌 API Endpoints

### Principais Endpoints

| Método | Endpoint | Descrição | Parâmetros |
|--------|----------|-----------|------------|
| GET | `/fixtures` | Lista partidas | `date`, `league` |
| GET | `/standings` | Classificação | `league`, `season` |
| GET | `/odds` | Odds de apostas | `fixture` |
| GET | `/team_stats` | Estatísticas do time | `team`, `league`, `season` |
| GET | `/topscorers` | Artilheiros | `league`, `season` |
| POST | `/analyze` | Análise completa | `fixture_id`, `options` |
| GET | `/predictions` | Previsões do dia | `date`, `confidence` |

### Códigos de Liga

| Liga | Código | País |
|------|--------|------|
| Brasileirão Série A | 71 | Brasil |
| Brasileirão Série B | 72 | Brasil |
| Copa do Brasil | 73 | Brasil |
| Premier League | 39 | Inglaterra |
| La Liga | 140 | Espanha |
| Champions League | 2 | Europa |

### Exemplo de Resposta

```json
{
  "ok": true,
  "source": "api-football",
  "data": {
    "fixture": {
      "id": 1035257,
      "date": "2025-11-05T00:30:00+00:00",
      "home": "Flamengo",
      "away": "Palmeiras"
    },
    "analysis": {
      "probabilities": {
        "home": 45.2,
        "draw": 27.8,
        "away": 27.0
      },
      "confidence": "HIGH",
      "value_bets": [
        {
          "outcome": "home",
          "odds": 2.35,
          "expected_value": 6.2,
          "kelly_stake": 2.5
        }
      ],
      "prediction": {
        "winner": "Flamengo",
        "goals_over_2.5": true,
        "btts": true
      }
    }
  }
}
```

## 🚢 Deploy

### Deploy no Render

1. Fork este repositório
2. Acesse [Render](https://render.com)
3. Crie um novo Web Service
4. Conecte seu repositório GitHub
5. Configure as variáveis de ambiente
6. Deploy automático a cada push

### Deploy no Heroku

```bash
# Instale o Heroku CLI
# https://devcenter.heroku.com/articles/heroku-cli

# Login
heroku login

# Crie a aplicação
heroku create seu-app-nome

# Configure variáveis
heroku config:set API_KEY=sua_chave_aqui

# Deploy
git push heroku main

# Abra a aplicação
heroku open
```

### Deploy com Docker

```bash
# Build da imagem
docker build -t gpt-apostas-futebol .

# Run container
docker run -d \
  -p 8080:8080 \
  -e API_KEY=sua_chave \
  --name apostas-api \
  gpt-apostas-futebol

# Ou use docker-compose para stack completo
docker-compose up -d
```

## 📊 Monitoramento

### Métricas Disponíveis

- **Prometheus**: http://localhost:9090
  - Taxa de requisições
  - Latência por endpoint
  - Taxa de erro
  - Uso de cache

- **Grafana**: http://localhost:3000
  - Dashboard de performance
  - Análise de apostas
  - ROI tracking
  - Alertas configuráveis

## 🧪 Testes

```bash
# Executar testes unitários
pytest tests/

# Executar com cobertura
pytest --cov=app tests/

# Executar testes de integração
pytest tests/integration/

# Linting
flake8 .
black .
```

## 🤝 Contribuindo

Contribuições são bem-vindas! Por favor, leia o [CONTRIBUTING.md](CONTRIBUTING.md) para detalhes sobre nosso código de conduta e processo de submissão de pull requests.

### Como Contribuir

1. Fork o projeto
2. Crie sua feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit suas mudanças (`git commit -m 'Add some AmazingFeature'`)
4. Push para a branch (`git push origin feature/AmazingFeature`)
5. Abra um Pull Request

## 📝 Licença

Este projeto está licenciado sob a Licença MIT - veja o arquivo [LICENSE](LICENSE) para detalhes.

## ⚠️ Disclaimer

**IMPORTANTE**: Este sistema é apenas para fins educacionais e de análise estatística. 

- Aposte com responsabilidade e dentro de seus limites
- O jogo pode causar dependência
- Proibido para menores de 18 anos
- Consulte as leis locais sobre apostas esportivas

## 📧 Suporte

- **Issues**: [GitHub Issues](https://github.com/seu-usuario/gpt-apostas-futebol-pro/issues)
- **Discussions**: [GitHub Discussions](https://github.com/seu-usuario/gpt-apostas-futebol-pro/discussions)
- **Email**: suporte@seudominio.com

## 🙏 Agradecimentos

- [API-Football](https://www.api-football.com/) pelos dados
- [Flask](https://flask.palletsprojects.com/) pelo framework
- [Redis](https://redis.io/) pelo cache
- Comunidade open source

---

**Desenvolvido com ❤️ para a comunidade de apostadores responsáveis**

![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)
![Flask](https://img.shields.io/badge/flask-%23000.svg?style=for-the-badge&logo=flask&logoColor=white)
![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?style=for-the-badge&logo=docker&logoColor=white)
![Redis](https://img.shields.io/badge/redis-%23DD0031.svg?style=for-the-badge&logo=redis&logoColor=white)
