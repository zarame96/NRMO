"""REST API + 画面。ジャービス等の外部アシスタントはこの REST か mcp_server.py から接続する。"""
from __future__ import annotations

import os
import secrets
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.responses import FileResponse

from . import data, hub
from . import modules  # noqa: F401  (モジュール自動登録)
from .modules import notes as notes_mod

app = FastAPI(title="stock-hub", version="0.1.0")
STATIC = Path(__file__).resolve().parent.parent / "static"


def auth(authorization: str | None = Header(default=None)):
    """STOCK_HUB_TOKEN を設定した場合のみ Bearer 認証を要求する(外部公開時は必ず設定)。"""
    token = os.environ.get("STOCK_HUB_TOKEN")
    if not token:
        return
    supplied = (authorization or "").removeprefix("Bearer ").strip()
    if not secrets.compare_digest(supplied, token):
        raise HTTPException(401, "unauthorized")


def _wrap(fn, *a, **kw):
    try:
        return fn(*a, **kw)
    except data.DataError as e:
        raise HTTPException(502, str(e))


@app.get("/api/health")
def health():
    return {"ok": True}


@app.get("/api/quote/{symbol}", dependencies=[Depends(auth)])
def quote(symbol: str):
    return _wrap(data.get_quote, symbol)


@app.get("/api/chart/{symbol}", dependencies=[Depends(auth)])
def chart(symbol: str, range: str = Query("3mo", pattern="^(5d|1mo|3mo|6mo|1y|5y)$")):
    return _wrap(data.get_chart, symbol, range)


@app.get("/api/news", dependencies=[Depends(auth)])
def news(q: str, limit: int = Query(10, ge=1, le=30), lang: str = Query("ja", pattern="^(ja|en)$")):
    return _wrap(data.get_news, q, limit, lang)


@app.get("/api/summary/{symbol}", dependencies=[Depends(auth)])
def summary(symbol: str, news_limit: int = Query(5, ge=1, le=20)):
    """株価+関連ニュースを1回で返す(アシスタント向け)。"""
    q = _wrap(data.get_quote, symbol)
    try:
        n = data.get_news(q["symbol"].split(".")[0] + " 株", news_limit)
    except data.DataError:
        n = []
    return {"quote": q, "news": n}


@app.get("/api/hub/tree", dependencies=[Depends(auth)])
def hub_tree():
    return hub.tree()


@app.get("/api/hub/{mid}", dependencies=[Depends(auth)])
def hub_run(mid: str):
    try:
        return hub.run(mid)
    except KeyError:
        raise HTTPException(404, "unknown module")


@app.patch("/api/hub/{mid}", dependencies=[Depends(auth)])
def hub_update(mid: str, patch: dict):
    """enabled / order / params を更新(例: {"enabled": false})。"""
    try:
        return hub.update(mid, patch)
    except KeyError:
        raise HTTPException(404, "unknown module")
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.post("/api/notes", dependencies=[Depends(auth)])
def notes_add(body: dict):
    try:
        return notes_mod.add_note(str(body.get("text", "")))
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.post("/api/notes/seeds", dependencies=[Depends(auth)])
def notes_seeds():
    try:
        return notes_mod.extract_seeds()
    except RuntimeError as e:
        raise HTTPException(503, str(e))
    except Exception as e:  # API障害等
        raise HTTPException(502, f"seed extraction failed: {type(e).__name__}")


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")
