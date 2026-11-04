"""株価・ニュース取得。外部APIが落ちても全体が死なないよう、全てエラーを例外で返す。"""
from __future__ import annotations

import os
import time
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from urllib.parse import quote

import httpx

UA = "stock-hub/0.1 (personal research tool)"
TTL = int(os.environ.get("STOCK_HUB_CACHE_SEC", "60"))
_cache: dict[str, tuple[float, object]] = {}


class DataError(Exception):
    pass


def _cached(key: str, fn):
    now = time.time()
    hit = _cache.get(key)
    if hit and now - hit[0] < TTL:
        return hit[1]
    val = fn()
    _cache[key] = (now, val)
    return val


def normalize_symbol(symbol: str) -> str:
    s = symbol.strip().upper()
    if not s or len(s) > 15 or not all(c.isalnum() or c in ".-=^" for c in s):
        raise DataError(f"invalid symbol: {symbol!r}")
    # 日本株: 4桁数字 → 7203 → 7203.T
    if s.isdigit() and len(s) == 4:
        s += ".T"
    return s


def _demo_chart(symbol: str, days: int) -> dict:
    import math

    base = 100 + sum(ord(c) for c in symbol) % 400
    closes = [round(base * (1 + 0.1 * math.sin(i / 6) + i * 0.001), 2) for i in range(days)]
    return {"symbol": symbol, "currency": "USD", "name": symbol + " (demo)",
            "dates": [f"day-{i}" for i in range(days)], "closes": closes}


def get_chart(symbol: str, range_: str = "3mo") -> dict:
    symbol = normalize_symbol(symbol)
    if os.environ.get("STOCK_HUB_DEMO") == "1":
        return _demo_chart(symbol, 60)

    def fetch():
        try:
            r = httpx.get(
                f"https://query1.finance.yahoo.com/v8/finance/chart/{quote(symbol)}",
                params={"range": range_, "interval": "1d"},
                headers={"User-Agent": UA},
                timeout=10,
            )
        except httpx.HTTPError as e:
            raise DataError(f"quote provider unreachable: {e}") from e
        if r.status_code == 429:
            raise DataError("quote provider rate-limited (429). 時間を置くか STOCK_HUB_DEMO=1 / 別プロバイダを使用")
        if r.status_code != 200:
            raise DataError(f"quote provider error {r.status_code}")
        res = (r.json().get("chart", {}).get("result") or [None])[0]
        if not res:
            raise DataError(f"no data for {symbol}")
        meta = res["meta"]
        ts = res.get("timestamp") or []
        closes = res["indicators"]["quote"][0].get("close") or []
        pairs = [(t, c) for t, c in zip(ts, closes) if c is not None]
        return {
            "symbol": symbol,
            "name": meta.get("longName") or meta.get("shortName") or symbol,
            "currency": meta.get("currency"),
            "dates": [time.strftime("%Y-%m-%d", time.gmtime(t)) for t, _ in pairs],
            "closes": [round(c, 4) for _, c in pairs],
        }

    return _cached(f"chart:{symbol}:{range_}", fetch)


def get_quote(symbol: str) -> dict:
    ch = get_chart(symbol)
    closes = ch["closes"]
    if len(closes) < 2:
        raise DataError("not enough data")
    last, prev = closes[-1], closes[-2]
    return {
        "symbol": ch["symbol"],
        "name": ch["name"],
        "currency": ch["currency"],
        "price": last,
        "prev_close": prev,
        "change": round(last - prev, 4),
        "change_pct": round((last / prev - 1) * 100, 2),
        "date": ch["dates"][-1],
    }


def get_news(query: str, limit: int = 10, lang: str = "ja") -> list[dict]:
    query = query.strip()
    if not query or len(query) > 100:
        raise DataError("invalid query")
    if os.environ.get("STOCK_HUB_DEMO") == "1":
        return [{"title": f"[demo] {query} news {i}", "link": "https://example.com",
                 "source": "demo", "published": None} for i in range(min(limit, 3))]
    hl, gl, ceid = ("ja", "JP", "JP:ja") if lang == "ja" else ("en-US", "US", "US:en")

    def fetch():
        try:
            r = httpx.get(
                "https://news.google.com/rss/search",
                params={"q": query, "hl": hl, "gl": gl, "ceid": ceid},
                headers={"User-Agent": UA},
                timeout=10,
                follow_redirects=True,
            )
            r.raise_for_status()
        except httpx.HTTPError as e:
            raise DataError(f"news provider error: {e}") from e
        items = []
        for it in ET.fromstring(r.content).iter("item"):
            pub = it.findtext("pubDate")
            try:
                pub = parsedate_to_datetime(pub).isoformat() if pub else None
            except (TypeError, ValueError):
                pass
            src = it.find("source")
            items.append({
                "title": it.findtext("title"),
                "link": it.findtext("link"),
                "source": src.text if src is not None else None,
                "published": pub,
            })
        return items

    return _cached(f"news:{query}:{lang}", fetch)[:limit]
