from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base

class UserModel(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Usar comillas simples para evitar problemas de carga circular o secuencial en SQLAlchemy
    sleep_logs = relationship("SleepLogModel", back_populates="usuario", cascade="all, delete-orphan")