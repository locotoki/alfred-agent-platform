from agent_core.ingest.chunker import chunk


def test_chunker_basic():
    txt = "word " * 8000
    chunks = chunk(txt)
    assert len(chunks) > 1
    assert all(chunks)
