from fastapi import APIRouter, HTTPException, status
# Importamos los nuevos modelos de sueño
from app.models.sleep import SleepLogCreate, SleepLogResponse

router = APIRouter()

# --- Endpoint de salud / monitoreo ---
@router.get("/health", status_code=status.HTTP_200_OK)
def health_check():
    """Endpoint de estado para verificar que la API está online."""
    return {"status": "ok", "message": "API activa y funcionando"}


# --- Rutas del Asistente de Sueño ---
@router.post("/sleep-logs", response_model=SleepLogResponse, status_code=status.HTTP_201_CREATED)
def create_sleep_log(log: SleepLogCreate):
    """Crea un nuevo registro de sueño para el usuario."""
    # Aquí llamarás a tu servicio (p. ej., SleepService) para procesar los datos
    pass