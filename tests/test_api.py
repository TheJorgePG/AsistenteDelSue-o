import uuid

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_check():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "message": "API activa y funcionando"}


def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert "Asistente" in response.text


def test_static_frontend_is_served():
    response = client.get("/static/app.js")

    assert response.status_code == 200
    assert "renderQuestions" in response.text


def test_pdf_content_endpoint():
    response = client.get("/api/v1/pdf/contenido")

    assert response.status_code == 200
    assert response.json()["longitud"] > 0


def test_chat_rejects_out_of_scope_request():
    response = client.post(
        "/api/v1/ai/chat",
        json={"pregunta": "Cuenta de uno a un millón."},
    )

    assert response.status_code == 200
    assert response.json()["rechazada"] is True
    assert response.json()["fragmentos_recuperados"] == 0


def test_chat_returns_retrieval_details(monkeypatch):
    from app.api import routes

    def fake_answer(**kwargs):
        assert kwargs["pregunta_usuario"] == "¿Cuántas horas se recomiendan?"
        assert kwargs["conversation_id"] == "conversation-test"
        return {
            "respuesta_asistente": "Entre 7 y 9 horas.",
            "rechazada": False,
            "motivo_rechazo": None,
            "confianza_similitud": 25.0,
            "umbral_confianza": 10.0,
            "fragmentos_recuperados": 1,
            "paginas_fuente": [1],
            "tiempos_ms": {"retrieval": 1.0, "generation": 2.0, "total": 3.0},
            "trace_id": "trace-test",
        }

    monkeypatch.setattr(routes.ai_service, "consultar_asistente", fake_answer)
    response = client.post(
        "/api/v1/ai/chat",
        json={
            "pregunta": "¿Cuántas horas se recomiendan?",
            "conversation_id": "conversation-test",
        },
    )

    assert response.status_code == 200
    assert response.json()["respuesta_asistente"] == "Entre 7 y 9 horas."
    assert response.json()["paginas_fuente"] == [1]
    assert response.json()["trace_id"] == "trace-test"


def test_chat_reports_generation_unavailable(monkeypatch):
    from app.api import routes
    from app.services.ai_assistant import AIGenerationError

    def unavailable(**kwargs):
        raise AIGenerationError("model unavailable")

    monkeypatch.setattr(routes.ai_service, "consultar_asistente", unavailable)
    response = client.post(
        "/api/v1/ai/chat",
        json={"pregunta": "¿Cuántas horas se recomiendan?"},
    )

    assert response.status_code == 503


def test_chat_rejects_invalid_question():
    response = client.post("/api/v1/ai/chat", json={"pregunta": ""})

    assert response.status_code == 422


def test_metrics_endpoint_reports_metric_groups():
    response = client.get("/api/v1/metrics")

    assert response.status_code == 200
    assert {"funcionales", "rag", "tecnicas"} <= response.json().keys()


def test_register_login_and_invalid_password():
    email = f"{uuid.uuid4().hex}@example.com"
    password = "test-password-123"
    registration = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password},
    )
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    invalid_login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "incorrect-password"},
    )

    assert registration.status_code == 200
    assert registration.json()["email"] == email
    assert login.status_code == 200
    assert login.json()["user_id"] > 0
    assert invalid_login.status_code == 401


def test_register_rejects_duplicate_email():
    email = f"{uuid.uuid4().hex}@example.com"
    payload = {"email": email, "password": "test-password-123"}
    first = client.post("/api/v1/auth/register", json=payload)
    duplicate = client.post("/api/v1/auth/register", json=payload)

    assert first.status_code == 200
    assert duplicate.status_code == 400