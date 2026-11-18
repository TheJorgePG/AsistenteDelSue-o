import os
import re
import time
import uuid
import logging
import importlib
import unicodedata
from app.services.pdf_parser import PDFParserService
from app.services.rag import SleepGuideRetriever
from app.services.observability import log_event, record_chat_event


class AIGenerationError(RuntimeError):
    pass


logger = logging.getLogger("asistente_sueno")

class AIAssistantService:
    def __init__(self):
        indexing_started = time.perf_counter()
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key:
            genai = importlib.import_module("google.generativeai")
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel(
                os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
            )
        else:
            self.model = None
        pdf_path = os.getenv("SLEEP_GUIDE_PDF", "app/data/documento_sueno.pdf")
        parser = PDFParserService(pdf_path=pdf_path)
        self.retriever = SleepGuideRetriever(
            parser.extract_pages(),
            top_k=int(os.getenv("RAG_TOP_K", "2")),
        )
        self.confidence_threshold = float(
            os.getenv("RAG_CONFIDENCE_THRESHOLD", "0.10")
        )
        if not 0 <= self.confidence_threshold <= 1:
            raise ValueError("RAG_CONFIDENCE_THRESHOLD debe estar entre 0 y 1")
        log_event(
            logging.INFO,
            "rag_index_ready",
            chunks_available=self.retriever.chunk_count,
            top_k=self.retriever.top_k,
            threshold_percent=round(self.confidence_threshold * 100, 2),
            duration_ms=round((time.perf_counter() - indexing_started) * 1000, 2),
        )

    def consultar_asistente(
        self,
        pregunta_usuario: str,
        datos_sueno_usuario: str = "",
        conversation_id: str | None = None,
    ) -> dict:
        trace_id = str(uuid.uuid4())
        conversation_id = conversation_id or trace_id
        started = time.perf_counter()
        normalized_question = unicodedata.normalize("NFKD", pregunta_usuario.lower())
        normalized_question = "".join(
            character for character in normalized_question
            if not unicodedata.combining(character)
        )
        direct_rejection = bool(
            re.search(r"\b(cuenta|contar|enumera|enumerar)\b", normalized_question)
            and re.search(r"\b(millon|millones|1000000|1\.000\.000)\b", normalized_question)
        )
        retrieved = [] if direct_rejection else self.retriever.retrieve(pregunta_usuario)
        confidence = retrieved[0].similarity if retrieved else 0.0
        retrieval_ms = (time.perf_counter() - started) * 1000
        accepted = bool(retrieved) and confidence >= self.confidence_threshold * 100
        rejection_reason = (
            "solicitud_fuera_de_alcance" if direct_rejection
            else "similitud_inferior_al_umbral" if not accepted
            else None
        )
        log_event(
            logging.INFO,
            "rag_retrieval",
            trace_id=trace_id,
            conversation_id=conversation_id,
            similarity_percent=confidence,
            threshold_percent=round(self.confidence_threshold * 100, 2),
            chunks_available=self.retriever.chunk_count,
            chunks_selected=len(retrieved) if accepted else 0,
            accepted=accepted,
            rejection_reason=rejection_reason,
            duration_ms=round(retrieval_ms, 2),
        )

        if not accepted:
            timings = {"retrieval": round(retrieval_ms, 2), "total": round(
                (time.perf_counter() - started) * 1000, 2
            )}
            record_chat_event(
                conversation_id=conversation_id,
                accepted=False,
                confidence=confidence,
                timings_ms=timings,
            )
            return {
                "respuesta_asistente": (
                    "No tengo información suficiente en la guía del sueño para "
                    "responder a esa pregunta. Puedo ayudarte con hábitos, duración "
                    "y calidad del descanso."
                ),
                "rechazada": True,
                "motivo_rechazo": rejection_reason,
                "confianza_similitud": confidence,
                "umbral_confianza": round(self.confidence_threshold * 100, 2),
                "fragmentos_recuperados": 0,
                "paginas_fuente": [],
                "tiempos_ms": timings,
                "trace_id": trace_id,
            }

        if self.model is None:
            timings = {
                "retrieval": round(retrieval_ms, 2),
                "total": round((time.perf_counter() - started) * 1000, 2),
            }
            record_chat_event(
                conversation_id=conversation_id,
                accepted=True,
                confidence=confidence,
                timings_ms=timings,
                error=True,
            )
            log_event(
                logging.ERROR,
                "rag_generation_unavailable",
                trace_id=trace_id,
                conversation_id=conversation_id,
                reason="gemini_api_key_missing",
            )
            raise AIGenerationError("GEMINI_API_KEY no está configurada")

        context = "\n\n".join(
            f"[Página {chunk.page}] {chunk.text}" for chunk in retrieved
        )
        prompt = f"""
        Eres un asistente del sueño. Contesta en español, de forma breve y concreta,
        usando únicamente la información de la guía incluida abajo. Si no permite
        responder, dilo claramente y no rellenes los huecos. Rechaza peticiones que
        no estén relacionadas con el sueño. No diagnostiques ni sustituyas a un
        profesional sanitario. No inventes datos.

        Fragmentos relevantes:
        {context}

        Datos de sueño aportados por el usuario: {datos_sueno_usuario}
        Pregunta: {pregunta_usuario}
        """

        generation_started = time.perf_counter()
        try:
            response = self.model.generate_content(prompt)
            answer = response.text
            if not answer:
                raise ValueError("Gemini devolvió una respuesta vacía")
        except Exception as error:
            generation_ms = (time.perf_counter() - generation_started) * 1000
            timings = {
                "retrieval": round(retrieval_ms, 2),
                "generation": round(generation_ms, 2),
                "total": round((time.perf_counter() - started) * 1000, 2),
            }
            record_chat_event(
                conversation_id=conversation_id,
                accepted=True,
                confidence=confidence,
                timings_ms=timings,
                error=True,
            )
            logger.error(
                "Fallo al generar respuesta de Gemini (trace_id=%s, tipo=%s)",
                trace_id,
                type(error).__name__,
            )
            raise AIGenerationError("No se pudo generar la respuesta") from error

        generation_ms = (time.perf_counter() - generation_started) * 1000
        timings = {
            "retrieval": round(retrieval_ms, 2),
            "generation": round(generation_ms, 2),
            "total": round((time.perf_counter() - started) * 1000, 2),
        }
        record_chat_event(
            conversation_id=conversation_id,
            accepted=True,
            confidence=confidence,
            timings_ms=timings,
        )
        log_event(
            logging.INFO,
            "rag_generation",
            trace_id=trace_id,
            conversation_id=conversation_id,
            duration_ms=timings["generation"],
            answer_length=len(answer),
        )
        return {
            "respuesta_asistente": answer,
            "rechazada": False,
            "motivo_rechazo": None,
            "confianza_similitud": confidence,
            "umbral_confianza": round(self.confidence_threshold * 100, 2),
            "fragmentos_recuperados": len(retrieved),
            "paginas_fuente": sorted({chunk.page for chunk in retrieved}),
            "tiempos_ms": timings,
            "trace_id": trace_id,
        }