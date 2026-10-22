"""The synthesis may only cite evidence it was shown -- anything else is a made-up source."""

import asyncio

from provenance.service import rerank


def _hits(n: int) -> list[dict]:
    return [
        {"match_type": "semantic", "payload": {"channel_name": "eng", "summary": f"thread {i}"}}
        for i in range(1, n + 1)
    ]


def _synthesize_with(monkeypatch, reply: dict, n_hits: int):
    async def fake_complete_json(*_args, **_kwargs):
        return reply

    monkeypatch.setattr(rerank.llm, "complete_json", fake_complete_json)
    return asyncio.run(rerank.synthesize(_hits(n_hits), "a retry constant"))


def test_in_range_citations_pass():
    assert rerank.uncited_references("set to 7s [1], see [2]", 2) == []


def test_out_of_range_citations_are_reported():
    assert rerank.uncited_references("per [1] and [4], not [0]", 3) == [0, 4]


def test_synthesis_citing_missing_evidence_is_dropped(monkeypatch):
    synthesis, _ = _synthesize_with(monkeypatch, {"synthesis": "Because of [3]."}, 2)
    assert synthesis is None


def test_grounded_synthesis_is_kept(monkeypatch):
    synthesis, _ = _synthesize_with(monkeypatch, {"synthesis": "Because of [2]."}, 2)
    assert synthesis == "Because of [2]."
