import os

os.environ["STOCK_HUB_DEMO"] = "1"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import hub  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(autouse=True)
def tmp_data(tmp_path, monkeypatch):
    monkeypatch.setattr(hub, "DATA_DIR", tmp_path)
    monkeypatch.setattr(hub, "CONFIG_PATH", tmp_path / "config.json")


c = TestClient(app)


def test_tree_has_categories():
    ids = {m["id"] for cat in c.get("/api/hub/tree").json() for m in cat["modules"]}
    assert {"finance.stock", "finance.bond", "finance.gold", "finance.crypto",
            "news.topics", "net.tech", "net.instagram", "notes.memo"} <= ids


def test_toggle_persists_and_disables():
    assert c.patch("/api/hub/finance.gold", json={"enabled": False}).json()["enabled"] is False
    assert c.get("/api/hub/finance.gold").json()["type"] == "message"
    assert hub.CONFIG_PATH.exists()


def test_params_and_validation():
    r = c.patch("/api/hub/news.topics", json={"params": {"topics": ["EV"]}}).json()
    assert r["params"]["topics"] == ["EV"] and r["params"]["limit"] == 5
    assert c.patch("/api/hub/news.topics", json={"enabled": "x"}).status_code == 400
    assert c.patch("/api/hub/nope", json={}).status_code == 404
    assert c.get("/api/hub/nope").status_code == 404


def test_modules_run():
    for mid in ["finance.stock", "finance.crypto", "news.topics", "net.tech"]:
        assert c.get(f"/api/hub/{mid}").status_code == 200


def test_notes_flow(monkeypatch):
    assert c.post("/api/notes", json={"text": ""}).status_code == 400
    c.post("/api/notes", json={"text": "毎回請求書作成が面倒"})
    assert c.get("/api/hub/notes.memo").json()["items"][0]["text"].startswith("毎回")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert c.post("/api/notes/seeds").status_code == 503
