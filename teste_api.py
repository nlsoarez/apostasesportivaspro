import requests
import json
from datetime import datetime

# URL da sua API no Render
BASE_URL = "https://apostasesportivaspro.onrender.com"

# Cores para o terminal
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
END = '\033[0m'

print("=" * 60)
print(f"{BLUE}🧪 TESTANDO API APOSTAS ESPORTIVAS PRO{END}")
print("=" * 60)

def testar_endpoint(nome, url, descricao=""):
    """Testa um endpoint e mostra o resultado"""
    print(f"\n{YELLOW}Testando: {nome}{END}")
    if descricao:
        print(f"  {descricao}")
    print(f"  URL: {url}")
    
    try:
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            print(f"  {GREEN}✅ Status: {response.status_code} - OK{END}")
            
            # Mostra preview dos dados
            data = response.json()
            
            if isinstance(data, dict):
                # Mostra apenas as primeiras chaves
                keys = list(data.keys())[:5]
                print(f"  Dados retornados: {keys}")
                
                if 'ok' in data:
                    print(f"  Status API: {'✅ OK' if data['ok'] else '❌ Erro'}")
                    
                if 'total' in data:
                    print(f"  Total de registros: {data['total']}")
                    
            return True
            
        else:
            print(f"  {RED}❌ Status: {response.status_code}{END}")
            print(f"  Erro: {response.text[:200]}")
            return False
            
    except requests.exceptions.Timeout:
        print(f"  {RED}❌ Timeout - API demorou muito para responder{END}")
        return False
        
    except requests.exceptions.ConnectionError:
        print(f"  {RED}❌ Erro de conexão - API pode estar offline{END}")
        return False
        
    except Exception as e:
        print(f"  {RED}❌ Erro: {e}{END}")
        return False

# Lista de testes
testes = []

# 1. Teste da página inicial
print(f"\n{BLUE}📋 1. TESTANDO PÁGINA INICIAL{END}")
resultado = testar_endpoint(
    "Página Inicial",
    f"{BASE_URL}/",
    "Deve retornar informações da API e endpoints disponíveis"
)
testes.append(("Página Inicial", resultado))

# 2. Teste de health check
print(f"\n{BLUE}📋 2. TESTANDO HEALTH CHECK{END}")
resultado = testar_endpoint(
    "Health Check",
    f"{BASE_URL}/health",
    "Verifica se a API está saudável"
)
testes.append(("Health Check", resultado))

# 3. Teste de fixtures (jogos de hoje)
print(f"\n{BLUE}📋 3. TESTANDO BUSCA DE JOGOS{END}")
hoje = datetime.now().strftime('%Y-%m-%d')
resultado = testar_endpoint(
    "Fixtures (Jogos)",
    f"{BASE_URL}/fixtures?date={hoje}&league=71",
    f"Buscando jogos do Brasileirão para hoje ({hoje})"
)
testes.append(("Fixtures", resultado))

# 4. Teste de classificação
print(f"\n{BLUE}📋 4. TESTANDO CLASSIFICAÇÃO{END}")
resultado = testar_endpoint(
    "Standings (Classificação)",
    f"{BASE_URL}/standings?league=71&season=2024",
    "Buscando tabela do Brasileirão 2024"
)
testes.append(("Classificação", resultado))

# 5. Teste de times
print(f"\n{BLUE}📋 5. TESTANDO LISTA DE TIMES{END}")
resultado = testar_endpoint(
    "Teams (Times)",
    f"{BASE_URL}/teams?league=71&season=2024",
    "Buscando times do Brasileirão 2024"
)
testes.append(("Times", resultado))

# 6. Teste de artilheiros
print(f"\n{BLUE}📋 6. TESTANDO ARTILHEIROS{END}")
resultado = testar_endpoint(
    "Top Scorers (Artilheiros)",
    f"{BASE_URL}/players/topscorers?league=71&season=2024",
    "Buscando artilheiros do Brasileirão 2024"
)
testes.append(("Artilheiros", resultado))

# Resumo dos testes
print("\n" + "=" * 60)
print(f"{BLUE}📊 RESUMO DOS TESTES{END}")
print("=" * 60)

total_ok = sum(1 for _, resultado in testes if resultado)
total_erro = len(testes) - total_ok

for nome, resultado in testes:
    status = f"{GREEN}✅ OK{END}" if resultado else f"{RED}❌ FALHOU{END}"
    print(f"  {nome}: {status}")

print("\n" + "-" * 40)
print(f"Total de testes: {len(testes)}")
print(f"{GREEN}Sucesso: {total_ok}{END}")
print(f"{RED}Falhas: {total_erro}{END}")

if total_ok == len(testes):
    print(f"\n{GREEN}🎉 TODOS OS TESTES PASSARAM! A API ESTÁ FUNCIONANDO!{END}")
elif total_ok > 0:
    print(f"\n{YELLOW}⚠️ ALGUNS TESTES FALHARAM. VERIFIQUE OS ERROS ACIMA.{END}")
else:
    print(f"\n{RED}❌ TODOS OS TESTES FALHARAM. A API PODE ESTAR OFFLINE.{END}")

print("\n" + "=" * 60)

# Instruções adicionais
if total_erro > 0:
    print(f"\n{YELLOW}💡 DICAS PARA RESOLVER PROBLEMAS:{END}")
    print("1. Verifique se a API Key está configurada no Render")
    print("2. Verifique se o serviço está ativo no Render Dashboard")
    print("3. Aguarde alguns minutos se acabou de fazer deploy")
    print("4. Verifique os logs no Render para mais detalhes")
    print(f"5. Acesse: https://dashboard.render.com/")
