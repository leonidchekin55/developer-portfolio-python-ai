from fastapi.testclient import TestClient

from app.main import app


def test_public_demo_sessions_are_isolated_and_support_board_actions():
    with TestClient(app) as client:
        first = client.post("/api/v1/demo/session").json()["access_token"]
        second = client.post("/api/v1/demo/session").json()["access_token"]
        first_headers = {"Authorization": f"Bearer {first}"}
        second_headers = {"Authorization": f"Bearer {second}"}

        initial = client.get("/api/v1/demo/board", headers=first_headers).json()
        project = client.post("/api/v1/demo/projects", headers=first_headers, json={"name": "Test project"})
        assert project.status_code == 201
        task = client.post("/api/v1/demo/tasks", headers=first_headers,
                           json={"project_id": project.json()["id"], "title": "Test task"})
        assert task.status_code == 201
        moved = client.patch(f"/api/v1/demo/tasks/{task.json()['id']}", headers=first_headers,
                             json={"status": "doing"})
        assert moved.json()["status"] == "doing"
        assert len(client.get("/api/v1/demo/board", headers=second_headers).json()["projects"]) == 2

        reset = client.post("/api/v1/demo/reset", headers=first_headers)
        assert reset.status_code == 200
        assert len(client.get("/api/v1/demo/board", headers=first_headers).json()["tasks"]) == 4
        assert initial["tasks"]


def test_public_demo_token_cannot_access_regular_api():
    with TestClient(app) as client:
        token = client.post("/api/v1/demo/session").json()["access_token"]
        response = client.get("/api/v1/me", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 401
