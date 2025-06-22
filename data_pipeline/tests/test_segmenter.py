from data_pipeline.segmenter import chunk_text

def test_chunk_text_basic():
    text = "This is a simple sentence. " * 20
    chunks = chunk_text(text, size=10)
    assert all(len(c.split()) <= 10 for c in chunks)
    assert sum(len(c.split()) for c in chunks) == 100
