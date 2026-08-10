from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class SleepLogBase(BaseModel):
    sleep_start: datetime = Field(..., description="Fecha y hora en la que el usuario se durmió")
    sleep_end: datetime = Field(..., description="Fecha y hora en la que el usuario se despertó")
    quality_score: int = Field(..., ge=1, le=10, description="Puntuación de calidad del sueño del 1 al 10")
    notes: Optional[str] = Field(None, max_length=500, description="Notas adicionales (p. ej., 'Tomé café muy tarde')")

class SleepLogCreate(SleepLogBase):
    """Modelo recibido en el POST para registrar un nuevo sueño. 
    No incluye ID ni tiempos calculados por el backend."""
    pass

class SleepLogResponse(SleepLogBase):
    """Modelo de respuesta para la API."""
    id: int
    duration_hours: float = Field(..., description="Horas totales calculadas por el servidor")
    created_at: datetime

    class Config:
        from_attributes = True