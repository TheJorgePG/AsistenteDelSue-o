from fastapi.testclient import TestClient
from app.main import app

#Puebas unitarias nativas con TestClient de FastAPI

client = TestClient(app)

def test_health_check():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "message": "API activa y funcionando"}

def test_root():
    response = client.get("/")
    assert response.status_code == 200