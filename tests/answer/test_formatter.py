from agent_core.answer.formatter import assemble_answer

def test_assemble_basic():
    passages = [
        {"id": 1, "snippet": "Paris is the capital of France.", "score": 0.9},
        {"id": 2, "snippet": "France is in Europe.", "score": 0.8},
    ]
    out = assemble_answer("What is the capital of France?", passages)
    assert "Paris" in out["answer"]
    assert len(out["citations"]) == 2
