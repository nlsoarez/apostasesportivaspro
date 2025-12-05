# 🎓 Guia do Sistema de Aprendizado - Apostas Esportivas Pro

## 📋 Índice
- [Introdução](#introdução)
- [Configuração Inicial](#configuração-inicial)
- [Endpoints Disponíveis](#endpoints-disponíveis)
- [Fluxo de Uso](#fluxo-de-uso)
- [Exemplos Práticos](#exemplos-práticos)
- [Métricas e Dashboard](#métricas-e-dashboard)
- [Boas Práticas](#boas-práticas)

---

## 🎯 Introdução

O **Sistema de Aprendizado** permite que a API aprenda com suas predições ao longo do tempo, rastreando:
- ✅ Acurácia das predições
- 💰 ROI (Retorno sobre Investimento)
- 📊 Calibração de confiança
- 🔍 Padrões e insights

### O que mudou?

**ANTES:**
```
Request → Análise → Response → 💨 Esquecido
```

**AGORA:**
```
Request → Análise → Response → 💾 Salvo no DB
                                    ↓
                            Verificação de Resultado
                                    ↓
                            Cálculo de Métricas
                                    ↓
                            Aprendizado e Melhoria
```

---

## ⚙️ Configuração Inicial

### 1. Instalar Dependências

```bash
pip install -r requirements.txt
```

Isso instala:
- `SQLAlchemy==2.0.23` - ORM para banco de dados
- `alembic==1.13.1` - Migrations (futuro)

### 2. Inicializar Banco de Dados

**Opção A - Automático (ao iniciar a API):**
```bash
python main.py
# O banco é criado automaticamente na primeira execução
```

**Opção B - Manual:**
```bash
python setup_db.py init
```

**Opção C - Com dados de exemplo:**
```bash
python setup_db.py sample
```

### 3. Verificar Status

```bash
python setup_db.py stats
```

Saída:
```
📈 Estatísticas do banco de dados:
  Total de predições: 2
  Predições verificadas: 1
  Predições corretas: 1
  Acurácia: 100.0%
  Total de insights: 1
```

### 4. Configuração de Ambiente

**Desenvolvimento (SQLite - padrão):**
```env
# Não precisa configurar nada - usa SQLite local
```

**Produção (PostgreSQL):**
```env
DATABASE_URL=postgresql://user:password@host:5432/dbname
```

---

## 🔌 Endpoints Disponíveis

### 1. Salvar Predição

**`POST /predictions/save`**

Salva uma nova predição no sistema.

**Request Body:**
```json
{
  "fixture_id": 12345,
  "prediction_type": "corners",
  "prediction_value": 10.5,
  "prediction_line": "Over",
  "recommended_bet": "Over 10.5 escanteios",
  "confidence": 0.72,
  "must_win_home": 6.5,
  "must_win_away": 3.0,
  "must_win_home_level": "HIGH",
  "must_win_away_level": "LOW",
  "odds_value": 1.85,
  "expected_value": 0.33,
  "league_id": 71,
  "season": 2025,
  "fixture_date": "2025-12-06T20:00:00",
  "metadata": {
    "teams": {
      "home": "Flamengo",
      "away": "Palmeiras"
    }
  }
}
```

**Response:**
```json
{
  "ok": true,
  "message": "Prediction saved successfully",
  "data": {
    "id": 1,
    "fixture_id": 12345,
    "prediction_type": "corners",
    "verified": false,
    "created_at": "2025-12-05T10:30:00"
  }
}
```

### 2. Verificar Predição

**`POST /predictions/verify/<prediction_id>`**

Marca uma predição como verificada com o resultado real.

**Request Body:**
```json
{
  "actual_result": 12.0,
  "stake": 1.0
}
```

**Response:**
```json
{
  "ok": true,
  "message": "Prediction verified successfully",
  "data": {
    "id": 1,
    "was_correct": true,
    "profit_loss": 0.85,
    "verified_at": "2025-12-06T22:30:00"
  }
}
```

### 3. Verificar Partida Completa

**`POST /predictions/verify-fixture/<fixture_id>`**

Verifica todas as predições de uma partida de uma vez.

**Request Body:**
```json
{
  "corners": 12.0,
  "cards": 5.0,
  "goals": 3.0
}
```

**Response:**
```json
{
  "ok": true,
  "message": "Verified 3 predictions",
  "data": [
    {"id": 1, "prediction_type": "corners", "was_correct": true},
    {"id": 2, "prediction_type": "cards", "was_correct": false},
    {"id": 3, "prediction_type": "goals", "was_correct": true}
  ]
}
```

### 4. Consultar Métricas

**`GET /predictions/metrics?type=corners&days=30`**

Retorna métricas de performance.

**Query Parameters:**
- `type` (opcional): Tipo de predição (corners, cards, value, goals)
- `days` (opcional): Período em dias (padrão: 30)
- `must_win_level` (opcional): Filtrar por nível Must Win (CRITICAL, HIGH, MODERATE, LOW)

**Response:**
```json
{
  "ok": true,
  "data": {
    "period": {
      "days": 30,
      "since": "2025-11-05T00:00:00",
      "until": "2025-12-05T00:00:00"
    },
    "volume": {
      "total_predictions": 150,
      "verified": 120,
      "pending": 30
    },
    "accuracy": {
      "correct": 78,
      "incorrect": 42,
      "accuracy_rate": 0.65
    },
    "confidence": {
      "average": 0.68,
      "calibration": {
        "60-70%": {
          "predicted": 0.65,
          "actual": 0.58,
          "count": 50
        },
        "70-80%": {
          "predicted": 0.75,
          "actual": 0.73,
          "count": 40
        }
      }
    },
    "financial": {
      "total_profit_loss": 9.6,
      "roi": 0.08,
      "roi_percentage": 8.0
    },
    "by_must_win_level": {
      "CRITICAL": {
        "count": 25,
        "accuracy": 0.72,
        "avg_confidence": 0.75
      },
      "HIGH": {
        "count": 45,
        "accuracy": 0.67,
        "avg_confidence": 0.70
      }
    }
  }
}
```

### 5. Dashboard

**`GET /predictions/dashboard?days=30`**

Retorna dados consolidados com recomendações automáticas.

**Response:**
```json
{
  "ok": true,
  "data": {
    "overall": {
      "volume": {"total_predictions": 500, "verified": 380},
      "accuracy": {"accuracy_rate": 0.61}
    },
    "by_type": {
      "corners": {
        "accuracy": 0.65,
        "roi": 0.08,
        "count": 200,
        "avg_confidence": 0.68
      },
      "cards": {
        "accuracy": 0.58,
        "roi": -0.02,
        "count": 180
      }
    },
    "insights": [
      {
        "title": "Times com Must Win CRITICAL têm 72% de acerto",
        "description": "...",
        "impact": "high"
      }
    ],
    "recommendations": [
      {
        "type": "success",
        "message": "Método 'corners' tem excelente performance (ROI: 8.0%)"
      },
      {
        "type": "warning",
        "message": "Método 'cards' com ROI negativo (-2.0%) - revisar fórmulas"
      }
    ]
  }
}
```

### 6. Listar Predições

**`GET /predictions/list?type=corners&verified=true&limit=50`**

Lista predições com filtros.

**Query Parameters:**
- `fixture_id`: Filtrar por partida
- `type`: Tipo de predição
- `verified`: true/false
- `limit`: Máximo de resultados (padrão: 50, máx: 200)
- `offset`: Skip de resultados (padrão: 0)

### 7. Buscar Predição

**`GET /predictions/<prediction_id>`**

Retorna uma predição específica.

### 8. Insights

**`GET /predictions/insights?type=pattern&limit=20`**

Lista insights de aprendizado.

**`POST /predictions/insights`**

Cria um novo insight manualmente.

---

## 🔄 Fluxo de Uso

### Cenário Típico

```
1️⃣ Usuário pede análise de escanteios
   ↓
2️⃣ Sistema faz análise (endpoint /analysis/corners)
   ↓
3️⃣ Sistema auto-salva predição (helper)
   ↓
4️⃣ Retorna análise para usuário
   ↓
5️⃣ Partida acontece
   ↓
6️⃣ Sistema ou usuário verifica resultado
   ↓
7️⃣ Predição marcada como correta/incorreta
   ↓
8️⃣ Métricas são atualizadas automaticamente
   ↓
9️⃣ Dashboard mostra performance e recomendações
```

---

## 💡 Exemplos Práticos

### Exemplo 1: Workflow Manual Completo

```bash
# 1. Fazer uma predição (via análise ou manualmente)
curl -X POST http://localhost:5000/predictions/save \
  -H "Content-Type: application/json" \
  -d '{
    "fixture_id": 12345,
    "prediction_type": "corners",
    "prediction_value": 10.5,
    "prediction_line": "Over",
    "confidence": 0.72,
    "odds_value": 1.85
  }'

# Resposta: {"ok": true, "data": {"id": 42, ...}}

# 2. Partida acontece... 12 escanteios no total

# 3. Verificar resultado
curl -X POST http://localhost:5000/predictions/verify/42 \
  -H "Content-Type: application/json" \
  -d '{"actual_result": 12.0}'

# 4. Ver métricas atualizadas
curl http://localhost:5000/predictions/metrics?type=corners&days=7

# 5. Ver dashboard
curl http://localhost:5000/predictions/dashboard
```

### Exemplo 2: Auto-Save em Endpoints de Análise

```python
# No arquivo main.py - endpoint de análise de escanteios
from prediction_helper import auto_save_prediction, parse_must_win_level

@app.route("/analysis/corners")
def analyze_corners():
    # ... código de análise existente ...

    # Auto-salvar predição
    auto_save_prediction(
        fixture_id=fixture_id,
        prediction_type="corners",
        prediction_value=estimativa_final,
        prediction_line="Over" if estimativa_final > 10 else "Under",
        recommended_bet=recomendacao,
        confidence=confianca_ajustada,
        must_win_home=must_win_home_score,
        must_win_away=must_win_away_score,
        must_win_home_level=parse_must_win_level(must_win_home_score),
        must_win_away_level=parse_must_win_level(must_win_away_score),
        league_id=league_id,
        season=season
    )

    # Retornar análise normalmente
    return jsonify({...})
```

### Exemplo 3: Verificação em Batch

```python
import requests

# Buscar resultados de partidas finalizadas
fixtures = requests.get("http://localhost:5000/fixtures?status=FT&date=2025-12-05").json()

for fixture in fixtures['data']:
    fixture_id = fixture['fixture']['id']

    # Extrair estatísticas
    corners = fixture['statistics']['corners']['total']
    cards = fixture['statistics']['cards']['yellow'] + fixture['statistics']['cards']['red']
    goals = fixture['goals']['home'] + fixture['goals']['away']

    # Verificar todas as predições desta partida
    requests.post(
        f"http://localhost:5000/predictions/verify-fixture/{fixture_id}",
        json={
            "corners": corners,
            "cards": cards,
            "goals": goals
        }
    )

print("Verificações concluídas!")

# Ver resultados
dashboard = requests.get("http://localhost:5000/predictions/dashboard?days=1").json()
print(f"Acurácia hoje: {dashboard['data']['overall']['accuracy']['accuracy_rate'] * 100:.1f}%")
```

### Exemplo 4: Monitoramento de Performance

```python
import requests
import pandas as pd
import matplotlib.pyplot as plt

# Buscar métricas dos últimos 90 dias
response = requests.get("http://localhost:5000/predictions/metrics?days=90").json()
metrics = response['data']

# Criar DataFrame
df = pd.DataFrame([
    {
        'type': 'corners',
        'accuracy': metrics['accuracy']['accuracy_rate'],
        'roi': metrics['financial']['roi']
    },
    # ... outros tipos ...
])

# Plotar
df.plot(x='type', y=['accuracy', 'roi'], kind='bar')
plt.title('Performance por Tipo de Predição')
plt.show()
```

---

## 📊 Métricas e Dashboard

### Métricas Principais

#### 1. **Acurácia (Accuracy)**
```
Acurácia = Predições Corretas / Total Verificado
```
- **Meta:** 60%+
- **Excelente:** 65%+
- **Preocupante:** <55%

#### 2. **ROI (Return on Investment)**
```
ROI = (Lucro Total / Total Investido) × 100
```
- **Meta:** 5%+
- **Excelente:** 10%+
- **Prejuízo:** <0%

#### 3. **Calibração de Confiança**
```
Calibração = Confiança Prevista ≈ Acurácia Real
```

**Exemplo:**
- Se dizemos 70% de confiança, devemos acertar ~70% das vezes
- **Bem calibrado:** Diferença < 5%
- **Sobre-confiante:** Previsto > Real
- **Sub-confiante:** Previsto < Real

#### 4. **Sharpe Ratio** (futuro)
```
Sharpe = (Retorno Médio - Taxa Livre de Risco) / Desvio Padrão
```
- Mede retorno ajustado ao risco
- **Meta:** 1.0+

### Dashboard - Interpretação

#### ✅ Sinais Positivos
- ROI > 5% em qualquer categoria
- Acurácia > 60% com 50+ predições verificadas
- Calibração bem ajustada (diff < 5%)
- Must Win CRITICAL com acurácia > 70%

#### ⚠️ Sinais de Atenção
- ROI negativo com 20+ predições
- Acurácia < 55% consistentemente
- Sobre-confiança (previsto > real em 10%+)
- Taxa de verificação < 50%

#### 🚨 Sinais Críticos
- ROI < -10%
- Acurácia < 50% com 50+ predições
- Sistema prevê 80% mas acerta 50%

---

## ✨ Boas Práticas

### 1. Verificação de Resultados

**❌ NÃO:**
```python
# Verificar antes da partida terminar
verify_prediction(pred_id, actual_result=0)  # Partida ainda rolando!
```

**✅ SIM:**
```python
# Verificar apenas após partida finalizada
if fixture['status']['short'] == 'FT':
    verify_prediction(pred_id, actual_result=total_corners)
```

### 2. Confiança Calibrada

**❌ NÃO:**
```python
# Sempre mesma confiança
confidence = 0.75  # Hardcoded!
```

**✅ SIM:**
```python
# Confiança baseada em fatores
base_confidence = 0.60
if sample_size > 10:
    base_confidence += 0.05
if must_win_diff > 3:
    base_confidence += 0.10
confidence = min(base_confidence, 0.95)
```

### 3. Metadata Útil

**❌ NÃO:**
```python
metadata = {}
```

**✅ SIM:**
```python
metadata = {
    "teams": {"home": "Flamengo", "away": "Palmeiras"},
    "league": {"id": 71, "name": "Brasileirão"},
    "stats_used": {
        "home_corners_avg": 5.2,
        "away_corners_avg": 4.8
    },
    "formula_version": "2.0",
    "adjustment_factor": 0.5
}
```

### 4. Verificação Regular

**Configure um cron job:**
```bash
# crontab -e
0 2 * * * /path/to/verify_yesterday.py
```

```python
# verify_yesterday.py
import requests
from datetime import datetime, timedelta

yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
fixtures = requests.get(f"/fixtures?status=FT&date={yesterday}").json()

for fixture in fixtures['data']:
    # Verificar predições...
```

### 5. Monitoramento de Drift

```python
# Verificar se o modelo está degradando
current_month = get_metrics(days=30)['accuracy']['accuracy_rate']
last_month = get_metrics(days=60)['accuracy']['accuracy_rate']

if current_month < last_month - 0.05:  # 5% drop
    print("⚠️  ALERTA: Model drift detected!")
    print("Considere retreinar parâmetros")
```

---

## 🔧 Troubleshooting

### Problema: "Learning system not available"

**Causa:** SQLAlchemy não instalado

**Solução:**
```bash
pip install SQLAlchemy alembic
python setup_db.py init
```

### Problema: "Prediction already verified"

**Causa:** Tentando verificar uma predição já verificada

**Solução:**
- Verificar status antes: `GET /predictions/<id>`
- Se precisar corrigir, deletar e recriar (futuro: endpoint de update)

### Problema: "Database is locked"

**Causa:** SQLite em uso por múltiplos processos

**Solução:**
```bash
# Desenvolvimento: use apenas 1 worker
gunicorn main:app --workers 1

# Produção: migre para PostgreSQL
export DATABASE_URL=postgresql://...
```

### Problema: ROI sempre 0.0

**Causa:** `odds_value` não está sendo salvo

**Solução:**
```python
auto_save_prediction(
    # ...
    odds_value=1.85,  # ← Não esquecer!
    expected_value=(probability * 1.85) - 1
)
```

---

## 📈 Roadmap Futuro

### Fase 1: Fundação ✅
- [x] Banco de dados
- [x] Modelos SQLAlchemy
- [x] Endpoints de feedback
- [x] Métricas básicas

### Fase 2: Otimização 🔄
- [ ] Grid search de parâmetros
- [ ] A/B testing
- [ ] Retreinamento automático
- [ ] Detecção de drift

### Fase 3: Machine Learning 🔮
- [ ] Feature engineering
- [ ] Random Forest baseline
- [ ] XGBoost model
- [ ] Ensemble methods
- [ ] Model versioning

### Fase 4: Produção 🚀
- [ ] Migração PostgreSQL
- [ ] Cache Redis
- [ ] Monitoring (Prometheus)
- [ ] Alertas automáticos
- [ ] Dashboard web

---

## 📚 Referências

- **Documentação SQLAlchemy:** https://docs.sqlalchemy.org/
- **Kelly Criterion:** https://en.wikipedia.org/wiki/Kelly_criterion
- **Calibration Plot:** https://scikit-learn.org/stable/modules/calibration.html
- **Sharpe Ratio:** https://www.investopedia.com/terms/s/sharperatio.asp

---

**Dúvidas?** Abra uma issue no repositório ou consulte `ANALYSIS.md` para detalhes técnicos.

**Última atualização:** 2025-12-05
