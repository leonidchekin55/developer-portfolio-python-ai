import asyncio
import json
from types import SimpleNamespace

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app import rag
from app.models import Base, Document, DocumentChunk


def test_extractive_answers_include_source(monkeypatch, tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'rag-test.db'}")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def prepare_and_ask():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with session_factory() as db:
            document = Document(filename="guide.txt", status="indexed", chunk_count=1)
            db.add(document)
            await db.flush()
            text = "Бесплатное демо ищет фрагменты документов и показывает ссылки на источники."
            db.add(DocumentChunk(document_id=document.id, page=2, chunk_index=0, text=text,
                                 terms_json=json.dumps(rag._term_weights(text), ensure_ascii=False)))
            await db.commit()
        monkeypatch.setattr(rag, "Session", session_factory)
        result = await rag._ask_extractive("Как демо показывает источники документов?")
        await engine.dispose()
        return result

    answer, sources = asyncio.run(prepare_and_ask())
    assert "[Источник 1]" in answer
    assert sources[0]["filename"] == "guide.txt"
    assert sources[0]["page"] == 2


def test_openrouter_mode_falls_back_without_secret(monkeypatch):
    monkeypatch.setattr(rag.settings, "rag_mode", "openrouter")
    monkeypatch.setattr(rag.settings, "openrouter_api_key", "")
    assert rag.effective_rag_mode() == "extractive"
    monkeypatch.setattr(rag.settings, "rag_mode", "extractive")
    monkeypatch.setattr(rag.settings, "openrouter_api_key", "configured")
    assert rag.effective_rag_mode() == "openrouter"
    monkeypatch.setattr(rag.settings, "rag_mode", "groq")
    monkeypatch.setattr(rag.settings, "openrouter_api_key", "")
    assert rag.effective_rag_mode() == "extractive"


def test_openrouter_receives_only_retrieved_context(monkeypatch):
    monkeypatch.setattr(rag.settings, "openrouter_api_key", "test-secret")
    monkeypatch.setattr(rag, "_retrieve_extractive", lambda question: asyncio.sleep(0, result=[
        {"filename": "guide.txt", "page": 2, "text": "Срок хранения — 30 дней.", "score": 0.7}
    ]))
    captured = {}

    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"choices": [{"message": {"content": "Срок хранения — 30 дней. [Источник 1]"}}]}

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def post(self, url, headers, json):
            captured.update(url=url, headers=headers, payload=json)
            return FakeResponse()

    monkeypatch.setattr(rag.httpx, "AsyncClient", lambda **kwargs: FakeClient())
    answer, sources = asyncio.run(rag._ask_openrouter("Какой срок хранения?"))
    assert "[Источник 1]" in answer
    assert sources[0]["filename"] == "guide.txt"
    assert "Срок хранения — 30 дней." in captured["payload"]["messages"][1]["content"]
    assert "полный документ" not in captured["payload"]["messages"][1]["content"]
    assert captured["url"] == "https://openrouter.ai/api/v1/chat/completions"
    assert captured["headers"]["Authorization"] == "Bearer test-secret"
