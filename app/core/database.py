import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Obtiene la URL de conexión del entorno (configurada en docker-compose)
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://usuario_sueno:password_sueno@db:5432/sueno_db")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()