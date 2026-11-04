import os

os.environ["STOCK_HUB_DEMO"] = "1"

from fastapi.testclient import TestClient  # noqa: E402

from app import data  # noqa: E402
from app.main import app  # noqa: E402

c = TestClient(app)


def test_quote_and_summary():
    r = c.get("/api/quote/AAPL")
    assert r.status_code == 200 and r.json()["symbol"] == "AAPL"
    s = c.get("/api/summary/7203").json()
    assert s["quote"]["symbol"] == "7203.T" and s["news"]


def test_invalid_symbol():
    assert c.get("/api/quote/%3Cscript%3E").status_code == 502


def test_token_required(monkeypatch):
    monkeypatch.setenv("STOCK_HUB_TOKEN", "secret")
    assert c.get("/api/quote/AAPL").status_code == 401
    assert c.get("/api/quote/AAPL", headers={"Authorization": "Bearer secret"}).status_code == 200
    assert c.get("/api/health").status_code == 200


def test_normalize():
    assert data.normalize_symbol("7203") == "7203.T"
