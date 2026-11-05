from __future__ import annotations

import os

import httpx

from .. import data
from ..hub import module


@module("net.tech", "流行ツール(Hacker News)", {"limit": 10})
def tech(p):
    if os.environ.get("STOCK_HUB_DEMO") == "1":
        return {"type": "list", "items": [{"title": "[demo] tool", "link": "https://example.com", "meta": "0 pts"}]}
    try:
        ids = httpx.get("https://hacker-news.firebaseio.com/v0/topstories.json",
                        headers={"User-Agent": data.UA}, timeout=10).json()[: p["limit"]]
        items = []
        for i in ids:
            s = httpx.get(f"https://hacker-news.firebaseio.com/v0/item/{i}.json",
                          headers={"User-Agent": data.UA}, timeout=10).json() or {}
            items.append({"title": s.get("title"), "link": s.get("url") or f"https://news.ycombinator.com/item?id={i}",
                          "meta": f"{s.get('score', 0)} pts · {s.get('descendants', 0)} comments"})
        return {"type": "list", "items": items}
    except httpx.HTTPError as e:
        return {"type": "message", "text": f"取得失敗: {e}"}


# Instagram: 自分のビジネス/クリエイターアカウントの投稿のみ(公式Graph API、トークン必須)。
# 他人の投稿のスクレイピングは規約違反のため対応しない。
@module("net.instagram", "Instagram(自分の投稿)", {"limit": 10}, enabled=False)
def instagram(p):
    token = os.environ.get("INSTAGRAM_TOKEN")
    if not token:
        return {"type": "message", "text": "環境変数 INSTAGRAM_TOKEN(Instagram Graph APIのトークン)を設定してください"}
    try:
        r = httpx.get("https://graph.instagram.com/me/media",
                      params={"fields": "caption,permalink,timestamp", "limit": p["limit"], "access_token": token},
                      timeout=10)
        r.raise_for_status()
    except httpx.HTTPError as e:
        return {"type": "message", "text": "取得失敗(トークン期限切れの可能性): " + type(e).__name__}
    return {"type": "list", "items": [{"title": (m.get("caption") or "")[:80], "link": m["permalink"],
                                        "meta": m["timestamp"][:10]} for m in r.json().get("data", [])]}
