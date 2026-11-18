import json
import logging
import math
import threading
from collections import Counter, deque
from statistics import mean
from typing import Any


logger = logging.getLogger("asistente_sueno")
_MAX_EVENTS = 5000
_events: deque[dict[str, Any]] = deque(maxlen=_MAX_EVENTS)
_lock = threading.Lock()


def log_event(level: int, event: str, **fields: Any) -> None:
    logger.log(level, json.dumps({"event": event, **fields}, ensure_ascii=False))


def record_chat_event(
    *,
    conversation_id: str,
    accepted: bool,
    confidence: float,
    timings_ms: dict[str, float],
    error: bool = False,
) -> None:
    with _lock:
        _events.append({
            "conversation_id": conversation_id,
            "accepted": accepted,
            "confidence": confidence,
            "timings_ms": timings_ms,
            "error": error,
        })


def get_metrics(confidence_threshold: float) -> dict[str, Any]:
    with _lock:
        events = list(_events)

    accepted = sum(event["accepted"] for event in events)
    refused = len(events) - accepted
    turns_by_conversation = Counter(event["conversation_id"] for event in events)
    total_latencies = [event["timings_ms"].get("total", 0.0) for event in events]
    confidences = [
        event["confidence"] for event in events if event["confidence"] > 0
    ]

    def percentile(values: list[float], value: float) -> float | None:
        if not values:
            return None
        ordered = sorted(values)
        return round(ordered[max(0, math.ceil(value * len(ordered)) - 1)], 2)

    stage_averages = {}
    for stage in ("retrieval", "generation", "total"):
        samples = [
            event["timings_ms"][stage]
            for event in events
            if stage in event["timings_ms"]
        ]
        stage_averages[stage] = round(mean(samples), 2) if samples else None

    return {
        "ventana": {
            "solicitudes": len(events),
            "maximo": _MAX_EVENTS,
            "reinicio": "Los datos se reinician al reiniciar el proceso.",
        },
        "funcionales": {
            "consultas_que_superan_umbral": accepted,
            "rechazos_por_falta_de_contexto": refused,
            "turnos_medios_por_conversacion": (
                round(mean(turns_by_conversation.values()), 2)
                if turns_by_conversation else 0
            ),
        },
        "rag": {
            "umbral_similitud_porcentaje": round(confidence_threshold * 100, 2),
            "similitud_media_porcentaje": (
                round(mean(confidences), 2) if confidences else None
            ),
        },
        "tecnicas": {
            "latencia_media_ms_por_etapa": stage_averages,
            "latencia_total_p95_ms": percentile(total_latencies, 0.95),
            "errores": sum(event["error"] for event in events),
        },
    }
