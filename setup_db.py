#!/usr/bin/env python3
"""
Script para inicializar e gerenciar o banco de dados de learning
"""
import sys
import os
from datetime import datetime, timedelta

# Adicionar o diretório atual ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def init_database():
    """Inicializa o banco de dados criando todas as tabelas"""
    print("🔧 Inicializando banco de dados...")

    try:
        from database import init_db, engine, Base
        from models import Prediction, PerformanceMetrics, ModelParameters, LearningInsights

        print(f"📁 Database URL: {engine.url}")

        # Criar todas as tabelas
        Base.metadata.create_all(bind=engine)

        print("✅ Banco de dados criado com sucesso!")
        print("\nTabelas criadas:")
        print("  - predictions (predições)")
        print("  - performance_metrics (métricas agregadas)")
        print("  - model_parameters (parâmetros do modelo)")
        print("  - learning_insights (insights de aprendizado)")

        return True

    except Exception as e:
        print(f"❌ Erro ao criar banco de dados: {e}")
        return False


def add_sample_data():
    """Adiciona dados de exemplo para testar o sistema"""
    print("\n📊 Adicionando dados de exemplo...")

    try:
        from database import SessionLocal
        from learning_service import LearningService

        db = SessionLocal()

        # Exemplo 1: Predição de escanteios
        pred1 = LearningService.save_prediction(
            db=db,
            fixture_id=999001,
            league_id=71,
            season=2025,
            prediction_type="corners",
            prediction_value=10.5,
            prediction_line="Over",
            recommended_bet="Over 10.5 escanteios",
            confidence=0.72,
            must_win_home=6.5,
            must_win_away=3.0,
            must_win_home_level="HIGH",
            must_win_away_level="LOW",
            odds_value=1.85,
            expected_value=0.33,
            fixture_date=datetime.utcnow() + timedelta(hours=2),
            metadata={
                "teams": {"home": "Flamengo", "away": "Palmeiras"},
                "league": {"name": "Brasileirão Série A"}
            }
        )

        # Exemplo 2: Predição de cartões
        pred2 = LearningService.save_prediction(
            db=db,
            fixture_id=999002,
            league_id=39,
            season=2025,
            prediction_type="cards",
            prediction_value=5.5,
            prediction_line="Over",
            recommended_bet="Over 5.5 cartões",
            confidence=0.68,
            must_win_home=7.5,
            must_win_away=7.0,
            must_win_home_level="CRITICAL",
            must_win_away_level="HIGH",
            odds_value=1.90,
            expected_value=0.29,
            fixture_date=datetime.utcnow() + timedelta(hours=5),
            metadata={
                "teams": {"home": "Manchester City", "away": "Liverpool"},
                "league": {"name": "Premier League"}
            }
        )

        # Verificar primeira predição (simulando resultado)
        LearningService.verify_prediction(
            db=db,
            prediction_id=pred1.id,
            actual_result=12.0  # Houve 12 escanteios - predição correta!
        )

        # Criar um insight de exemplo
        LearningService.create_insight(
            db=db,
            insight_type="pattern",
            title="Times com Must Win CRITICAL têm maior acurácia em escanteios",
            description="Análise de 50 predições mostrou que quando ambos os times têm Must Win >= 7.0, a acurácia sobe para 72% comparado com 58% geral.",
            confidence=0.85,
            impact="high",
            prediction_type="corners",
            supporting_data={"sample_size": 50, "accuracy_high_pressure": 0.72, "accuracy_normal": 0.58},
            sample_size=50,
            expires_in_days=30
        )

        print(f"✅ Dados de exemplo adicionados:")
        print(f"   - 2 predições criadas (IDs: {pred1.id}, {pred2.id})")
        print(f"   - 1 predição verificada (ID: {pred1.id} - CORRETA)")
        print(f"   - 1 insight criado")

        db.close()
        return True

    except Exception as e:
        print(f"❌ Erro ao adicionar dados de exemplo: {e}")
        import traceback
        traceback.print_exc()
        return False


def show_stats():
    """Mostra estatísticas do banco de dados"""
    print("\n📈 Estatísticas do banco de dados:")

    try:
        from database import SessionLocal
        from models import Prediction, LearningInsights

        db = SessionLocal()

        total_predictions = db.query(Prediction).count()
        verified_predictions = db.query(Prediction).filter(Prediction.verified == True).count()
        correct_predictions = db.query(Prediction).filter(Prediction.was_correct == True).count()
        total_insights = db.query(LearningInsights).count()

        accuracy = (correct_predictions / verified_predictions * 100) if verified_predictions > 0 else 0

        print(f"  Total de predições: {total_predictions}")
        print(f"  Predições verificadas: {verified_predictions}")
        print(f"  Predições corretas: {correct_predictions}")
        print(f"  Acurácia: {accuracy:.1f}%")
        print(f"  Total de insights: {total_insights}")

        db.close()
        return True

    except Exception as e:
        print(f"❌ Erro ao buscar estatísticas: {e}")
        return False


def reset_database():
    """Remove e recria o banco de dados (CUIDADO!)"""
    print("\n⚠️  ATENÇÃO: Isso irá apagar TODOS os dados!")
    confirm = input("Digite 'CONFIRMAR' para continuar: ")

    if confirm != "CONFIRMAR":
        print("Operação cancelada.")
        return False

    try:
        from database import engine, Base

        print("🗑️  Removendo tabelas existentes...")
        Base.metadata.drop_all(bind=engine)

        print("🔧 Recriando tabelas...")
        Base.metadata.create_all(bind=engine)

        print("✅ Banco de dados resetado com sucesso!")
        return True

    except Exception as e:
        print(f"❌ Erro ao resetar banco de dados: {e}")
        return False


def main():
    """Menu principal"""
    print("=" * 60)
    print("  APOSTAS ESPORTIVAS PRO - Setup do Banco de Dados")
    print("=" * 60)

    if len(sys.argv) > 1:
        command = sys.argv[1]
    else:
        print("\nComandos disponíveis:")
        print("  init        - Inicializar banco de dados")
        print("  sample      - Adicionar dados de exemplo")
        print("  stats       - Mostrar estatísticas")
        print("  reset       - Resetar banco de dados (apaga tudo!)")
        print()
        command = input("Digite o comando: ").strip().lower()

    if command == "init":
        init_database()
    elif command == "sample":
        if init_database():
            add_sample_data()
    elif command == "stats":
        show_stats()
    elif command == "reset":
        reset_database()
    else:
        print(f"❌ Comando desconhecido: {command}")
        print("Use: init, sample, stats ou reset")
        sys.exit(1)


if __name__ == "__main__":
    main()
