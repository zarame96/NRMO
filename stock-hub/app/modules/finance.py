from __future__ import annotations

import os

import httpx

from .. import data
from ..hub import module

UA = data.UA


def _quotes(symbols: list[str]) -> dict:
    items, errors = [], []
    for s in symbols:
        try:
            items.append(data.get_quote(s))
        except data.DataError as e:
            errors.append(f"{s}: {e}")
    return {"type": "quotes", "items": items, "errors": errors}


@module("finance.stock", "株", {"symbols": ["AAPL", "NVDA", "7203"]})
def stock(p):
    return _quotes(p["symbols"])


# 債券: 米国債利回り指数(Yahoo: ^TNX=10年, ^FVX=5年, ^TYX=30年)。値は利回り(%)。
@module("finance.bond", "債券(米国債利回り)", {"symbols": ["^TNX", "^FVX", "^TYX"]})
def bond(p):
    return _quotes(p["symbols"])


# 金: 先物 GC=F
@module("finance.gold", "金", {"symbols": ["GC=F"]})
def gold(p):
    return _quotes(p["symbols"])


@module("finance.crypto", "コイン", {"ids": ["bitcoin", "ethereum"], "vs": "usd"})
def crypto(p):
    if os.environ.get("STOCK_HUB_DEMO") == "1":
        return {"type": "quotes", "items": [{"symbol": i, "name": i, "price": 1.0, "change_pct": 0.0,
                                              "currency": p["vs"].upper()} for i in p["ids"]], "errors": []}
    try:
        r = httpx.get("https://api.coingecko.com/api/v3/simple/price",
                      params={"ids": ",".join(p["ids"]), "vs_currencies": p["vs"], "include_24hr_change": "true"},
                      headers={"User-Agent": UA}, timeout=10)
        r.raise_for_status()
    except httpx.HTTPError as e:
        return {"type": "quotes", "items": [], "errors": [f"coingecko: {e}"]}
    j = r.json()
    items = [{"symbol": i, "name": i, "currency": p["vs"].upper(), "price": j[i][p["vs"]],
              "change_pct": round(j[i].get(f"{p['vs']}_24h_change", 0), 2)} for i in p["ids"] if i in j]
    return {"type": "quotes", "items": items, "errors": []}
