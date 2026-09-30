from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from fastapi.testclient import TestClient

from app import db as db_module, main, rag


def test_accounts_isolate_uploads_search_history_and_deletion(monkeypatch, tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'accounts.db'}")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    monkeypatch.setattr(main, "engine", engine)
    monkeypatch.setattr(main, "Session", session_factory)
    monkeypatch.setattr(db_module, "Session", session_factory)
    monkeypatch.setattr(rag, "Session", session_factory)
    monkeypatch.setattr(main.settings, "rag_mode", "extractive")
    monkeypatch.setattr(main.settings, "openrouter_api_key", "")
    monkeypatch.setattr(main.settings, "upload_dir", str(tmp_path / "uploads"))
    monkeypatch.setattr(rag, "client", None)

    with TestClient(main.app) as client_a, TestClient(main.app) as client_b:
        registered_a = client_a.post("/api/v1/auth/register", json={
            "email": "alice@example.test", "password": "alice-password-strong"
        })
        registered_b = client_b.post("/api/v1/auth/register", json={
            "email": "bob@example.test", "password": "bob-password-strong"
        })
        assert registered_a.status_code == 201
        assert registered_b.status_code == 201

        content = "Alice private project codeword foxglove is stored only in her workspace."
        uploaded = client_a.post("/api/v1/documents", files={
            "file": ("alice.txt", content, "text/plain")
        })
        assert uploaded.status_code == 200, uploaded.text
        document_id = uploaded.json()["id"]

        docs_a = client_a.get("/api/v1/documents").json()
        docs_b = client_b.get("/api/v1/documents").json()
        assert any(document["filename"] == "alice.txt" for document in docs_a)
        assert all(document["filename"] != "alice.txt" for document in docs_b)

        answer_a = client_a.post("/api/v1/chat", json={"question": "What is Alice's project codeword foxglove?"})
        assert answer_a.status_code == 200
        assert any(source["filename"] == "alice.txt" for source in answer_a.json()["sources"])

        answer_b = client_b.post("/api/v1/chat", json={"question": "What is Alice's project codeword foxglove?"})
        assert answer_b.status_code == 200
        assert all(source["filename"] != "alice.txt" for source in answer_b.json()["sources"])
        history_a = client_a.get("/api/v1/history").json()
        history_b = client_b.get("/api/v1/history").json()
        assert history_a and history_a[0]["answer"] == answer_a.json()["answer"]
        assert len(history_b) == 1
        assert history_b[0]["question"] == "What is Alice's project codeword foxglove?"
        assert all(source["filename"] != "alice.txt" for source in history_b[0]["sources"])

        assert client_b.delete(f"/api/v1/documents/{document_id}").status_code == 404
        assert any(document["filename"] == "alice.txt" for document in client_a.get("/api/v1/documents").json())
        assert client_a.delete(f"/api/v1/documents/{document_id}").status_code == 204
        assert all(document["filename"] != "alice.txt" for document in client_a.get("/api/v1/documents").json())
        assert client_a.get("/api/v1/history").json() == []

    import asyncio
    asyncio.run(engine.dispose())


def test_upload_rejects_untrusted_origin_and_invalid_text(monkeypatch, tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'upload-guard.db'}")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    monkeypatch.setattr(main, "engine", engine)
    monkeypatch.setattr(main, "Session", session_factory)
    monkeypatch.setattr(db_module, "Session", session_factory)
    monkeypatch.setattr(main.settings, "rag_mode", "extractive")
    monkeypatch.setattr(main.settings, "openrouter_api_key", "")
    monkeypatch.setattr(main.settings, "upload_dir", str(tmp_path / "uploads"))
    with TestClient(main.app) as client:
        assert client.post("/api/v1/auth/register", json={"email":"guard@example.test", "password":"strong-password-123"}).status_code == 201
        bad_origin = client.post("/api/v1/documents", headers={"Origin":"https://attacker.example"}, files={"file":("attack.txt", b"hello", "text/plain")})
        assert bad_origin.status_code == 403
        invalid_utf8 = client.post("/api/v1/documents", files={"file":("broken.txt", b"\xff\xfe", "text/plain")})
        assert invalid_utf8.status_code == 415
        empty = client.post("/api/v1/documents", files={"file":("empty.txt", b"", "text/plain")})
        assert empty.status_code == 422
        assert all(row["filename"] not in {"broken.txt", "empty.txt"} for row in client.get("/api/v1/documents").json())
    import asyncio
    asyncio.run(engine.dispose())


def test_cookie_authenticated_writes_reject_untrusted_origins(monkeypatch, tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'origin-guard.db'}")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    monkeypatch.setattr(main, "engine", engine)
    monkeypatch.setattr(main, "Session", session_factory)
    monkeypatch.setattr(db_module, "Session", session_factory)
    monkeypatch.setattr(main.settings, "rag_mode", "extractive")
    monkeypatch.setattr(main.settings, "openrouter_api_key", "")
    monkeypatch.setattr(main.settings, "upload_dir", str(tmp_path / "uploads"))
    async def fake_index(*args, **kwargs): return 1
    monkeypatch.setattr(main, "index_document", fake_index)
    with TestClient(main.app) as client:
        assert client.post("/api/v1/auth/register", json={"email":"origin@example.test", "password":"strong-password-123"}).status_code == 201
        headers={"Origin":"https://attacker.example"}
        assert client.post("/api/v1/chat", headers=headers, json={"question":"hello world"}).status_code == 403
        assert client.post("/api/v1/documents", headers=headers, files={"file":("attack.txt", b"hello", "text/plain")}).status_code == 403
        assert client.delete("/api/v1/documents/999", headers=headers).status_code == 403
        allowed={"Origin":"https://portfolio-knowledge-demo.onrender.com"}
        assert client.post("/api/v1/documents", headers=allowed, files={"file":("ok.txt", b"UTF-8 content", "text/plain")}).status_code == 200
    import asyncio
    asyncio.run(engine.dispose())
