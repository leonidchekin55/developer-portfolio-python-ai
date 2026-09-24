from app.rag import chunks_for
def test_chunks_overlap_and_cover_text():
 source="0123456789"*100; chunks=chunks_for(source,size=120,overlap=20)
 assert len(chunks)>1 and all(chunks)
 assert "0123456789"*3 in "".join(chunks)
def test_empty_chunking(): assert chunks_for("  ")==[]
