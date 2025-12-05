"""
Database configuration and session management
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.ext.declarative import declarative_base

# Database URL - SQLite para desenvolvimento, fácil migração para PostgreSQL
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///predictions.db")

# Criar engine
# check_same_thread=False necessário para SQLite com Flask
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
    echo=False,  # Set True para debug SQL
    pool_pre_ping=True,  # Verifica conexões antes de usar
    pool_recycle=3600  # Recicla conexões a cada hora
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Thread-safe session for Flask
db_session = scoped_session(SessionLocal)

# Base para modelos
Base = declarative_base()
Base.query = db_session.query_property()


def init_db():
    """
    Inicializa o banco de dados criando todas as tabelas
    """
    import models  # Import aqui para evitar circular dependency
    Base.metadata.create_all(bind=engine)


def get_db():
    """
    Dependency para obter sessão do banco
    Usar em context manager: with get_db() as db:
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def close_db():
    """
    Fecha a sessão do banco (útil para cleanup)
    """
    db_session.remove()
