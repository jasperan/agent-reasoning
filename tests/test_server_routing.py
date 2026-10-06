"""HTTP-level tests for the packaged gateway and the root server (need the server extra)."""

import importlib.util
import json
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")
from fastapi.testclient import TestClient  # noqa: E402

from agent_reasoning import server as packaged  # noqa: E402


class _FakeAgent:
    seen = []

    def __init__(self, model, **kwargs):
        _FakeAgent.seen.append(model)
        self.name = "Fake"
        self._debug_cancelled = False
        self._debug_event = None

    def stream(self, prompt):
        yield "hi"


def test_packaged_server_routes_strategies_missing_from_old_map(monkeypatch):
    monkeypatch.setitem(packaged.AGENT_MAP, "mcts", _FakeAgent)
    client = TestClient(packaged.app)
    resp = client.post("/api/generate", json={"model": "gemma3+mcts", "prompt": "q"})
    lines = [json.loads(line) for line in resp.text.splitlines()]
    assert _FakeAgent.seen[-1] == "gemma3"
    assert lines[0]["response"] == "hi"


def test_packaged_server_tags_list_every_primary_strategy():
    names = {m["name"].split("+", 1)[1] for m in TestClient(packaged.app).get("/api/tags").json()["models"]}
    assert {"mcts", "debate", "socratic", "meta", "refinement"} <= names


def test_root_server_drops_finished_debug_sessions():
    spec = importlib.util.spec_from_file_location(
        "root_server", Path(__file__).resolve().parent.parent / "server.py"
    )
    root = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(root)
    root.AGENT_MAP["standard"] = _FakeAgent
    client = TestClient(root.app)
    sid = client.post("/api/debug/start", json={"model": "m", "prompt": "q"}).json()["session_id"]
    while not client.post("/api/debug/step", json={"session_id": sid}).json()["done"]:
        pass
    assert sid not in root.debug_sessions
