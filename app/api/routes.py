from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.ai_assistant import AIAssistantService
from app.services.pdf_parser import PDFParserService

router = APIRouter()
ai_service = AIAssistantService()

class ConsultaRequest(BaseModel):
    pregunta: str
    sensaciones_diarias: str = "Sin datos adicionales"

@router.post("/ai/chat")
def chat_asistente_sueno(payload: ConsultaRequest):
    """Endpoint para chatear con Gemini utilizando el contexto del PDF."""
    try:
        respuesta = ai_service.consultar_asistente(
            pregunta_usuario=payload.pregunta,
            datos_sueno_usuario=payload.sensaciones_diarias
        )
        return {
            "status": "success",
            "respuesta_asistente": respuesta
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/pdf/contenido")
def leer_pdf_sueno():
    """Endpoint opcional para verificar el texto extraído del PDF."""
    try:
        parser = PDFParserService(pdf_path="app/data/documento_sueno.pdf")
        texto = parser.extract_text()
        return {"status": "success", "longitud": len(texto), "extracto": texto[:300]}
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))