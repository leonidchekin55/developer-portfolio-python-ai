import asyncio
import json

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
