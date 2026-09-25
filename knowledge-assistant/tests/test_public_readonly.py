import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app import main, rag


def test_public_demo_is_read_only_and_only_lists_sample(monkeypatch):
    monkeypatch.setattr(main.settings, "allow_public_uploads", False)
    assert main.mode()["uploads_enabled"] is False
    assert main.mode()["history_enabled"] is False

    class Rows:
        def scalars(self):
            return [SimpleNamespace(
                id=1, filename="demo-guide.txt", status="indexed", chunk_count=1,
                created_at=datetime.now(timezone.utc),
            )]

    class FakeDB:
        statement = None

        async def execute(self, statement):
            self.statement = str(statement)
            return Rows()

    db = FakeDB()
    documents = asyncio.run(main.documents(db))
    assert len(documents) == 1
    assert documents[0]["filename"] == "demo-guide.txt"
    assert "documents.filename =" in db.statement
    assert asyncio.run(main.history(20, db)) == []


def test_public_demo_rejects_uploads(monkeypatch):
    monkeypatch.setattr(main.settings, "allow_public_uploads", False)

    async def call_upload():
        await main.upload(file=None, db=None)

    with pytest.raises(HTTPException) as error:
        asyncio.run(call_upload())
    assert error.value.status_code == 403


def test_public_chat_does_not_persist_shared_history(monkeypatch):
    monkeypatch.setattr(main.settings, "allow_public_uploads", False)
    monkeypatch.setattr(main, "ask", lambda question: asyncio.sleep(0, result=("Ответ [Источник 1]", [])))

    class FakeDB:
        def add(self, record):
            raise AssertionError("read-only public chat must not persist conversations")

        async def commit(self):
            raise AssertionError("read-only public chat must not commit conversations")

    response = asyncio.run(main.chat(main.Question(question="Тестовый вопрос"), FakeDB()))
    assert response == {"answer": "Ответ [Источник 1]", "sources": []}


def test_public_retrieval_excludes_uploaded_documents(monkeypatch, tmp_path):
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    from app.models import Base, Document, DocumentChunk
    import json

    monkeypatch.setattr(rag.settings, "allow_public_uploads", False)
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'public-demo.db'}")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def prepare_and_retrieve():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with session_factory() as db:
            for filename, text in (
                ("demo-guide.txt", "Knowbase принимает PDF, DOCX и TXT."),
                ("other-visitor.pdf", "Секретные сведения другого посетителя."),
            ):
                doc = Document(filename=filename, status="indexed", chunk_count=1)
                db.add(doc)
                await db.flush()
                db.add(DocumentChunk(document_id=doc.id, page=1, chunk_index=0, text=text,
                                     terms_json=json.dumps(rag._term_weights(text), ensure_ascii=False)))
            await db.commit()
        monkeypatch.setattr(rag, "Session", session_factory)
        results = await rag._retrieve_extractive("Какие форматы файлов принимает Knowbase?")
        await engine.dispose()
        return results

    sources = asyncio.run(prepare_and_retrieve())
    assert sources
    assert all(source["filename"] == "demo-guide.txt" for source in sources)
