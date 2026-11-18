import csv
import os
from pathlib import Path

from app.services.ai_assistant import AIAssistantService
from app.services.pdf_parser import PDFParserService
from app.services.rag import SleepGuideRetriever


ROOT = Path(__file__).resolve().parents[1]


def test_retriever_returns_only_top_two_relevant_chunks():
    pages = PDFParserService(str(ROOT / "app/data/documento_sueno.pdf")).extract_pages()
    retriever = SleepGuideRetriever(pages, top_k=2)

    chunks = retriever.retrieve("¿Cuánto antes de dormir debería evitar la cafeína?")

    assert 0 < len(chunks) <= 2
    assert "cafeína" in chunks[0].text.lower()
    assert chunks[0].similarity > 0


def test_golden_dataset_matches_the_configured_acceptance_threshold():
    pages = PDFParserService(str(ROOT / "app/data/documento_sueno.pdf")).extract_pages()
    retriever = SleepGuideRetriever(pages)
    threshold = float(os.getenv("RAG_CONFIDENCE_THRESHOLD", "0.10")) * 100
    dataset_path = ROOT / "data/golden_dataset.csv"

    with dataset_path.open(newline="", encoding="utf-8") as dataset_file:
        for row in csv.DictReader(dataset_file):
            chunks = retriever.retrieve(row["pregunta"])
            accepted = bool(chunks) and chunks[0].similarity >= threshold
            if row["comportamiento_esperado"] == "responder":
                assert accepted, row["id"]
            else:
                assert not accepted, row["id"]


def test_counting_to_a_million_is_rejected_without_calling_the_model(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "")
    service = AIAssistantService()

    result = service.consultar_asistente("Cuenta de uno a un millón.")

    assert result["rechazada"] is True
    assert result["fragmentos_recuperados"] == 0
    assert result["motivo_rechazo"] == "solicitud_fuera_de_alcance"


def test_generation_receives_only_retrieved_fragments(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "")
    service = AIAssistantService()

    class ModelStub:
        prompt = ""

        def generate_content(self, prompt):
            self.prompt = prompt
            return type("Response", (), {"text": "Entre 7 y 9 horas."})()

    model = ModelStub()
    service.model = model
    result = service.consultar_asistente(
        "¿Cuántas horas de sueño se recomiendan para una persona adulta?"
    )
    full_guide = PDFParserService(
        str(ROOT / "app/data/documento_sueno.pdf")
    ).extract_text()

    assert result["rechazada"] is False
    assert result["fragmentos_recuperados"] <= 2
    assert "Entre 7 y 9 horas." == result["respuesta_asistente"]
    assert len(model.prompt) < len(full_guide)
    assert "Fragmentos relevantes:" in model.prompt
