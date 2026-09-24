from fastapi.testclient import TestClient
from app.main import app

def test_live():
    response = TestClient(app).get("/health/live")
    assert response.json() == {"status": "ok"}
