from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from app.services.ai_assistant import AIAssistantService, AIGenerationError
from app.services.observability import get_metrics
from app.services.pdf_parser import PDFParserService

router = APIRouter()
ai_service = AIAssistantService()

class ConsultaRequest(BaseModel):
    pregunta: str = Field(..., min_length=1, max_length=1000)
    sensaciones_diarias: str = "Sin datos adicionales"
    conversation_id: str | None = Field(default=None, min_length=1, max_length=128)

@router.post("/ai/chat")
def chat_asistente_sueno(payload: ConsultaRequest):
    """Responde usando solo los fragmentos relevantes de la guía."""
    try:
        result = ai_service.consultar_asistente(
            pregunta_usuario=payload.pregunta,
            datos_sueno_usuario=payload.sensaciones_diarias,
            conversation_id=payload.conversation_id,
        )
        return {"status": "success", **result}
    except AIGenerationError as error:
        raise HTTPException(
            status_code=503,
            detail="El servicio de generación no está disponible. Inténtalo más tarde.",
        ) from error

@router.get("/pdf/contenido")
def leer_pdf_sueno():
    """Endpoint opcional para verificar el texto extraído del PDF."""
    try:
        parser = PDFParserService(pdf_path="app/data/documento_sueno.pdf")
        texto = parser.extract_text()
        return {"status": "success", "longitud": len(texto), "extracto": texto[:300]}
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/health")
def health_check():
    return {"status": "ok", "message": "API activa y funcionando"}


@router.get("/metrics")
def metricas():
    return get_metrics(ai_service.confidence_threshold)