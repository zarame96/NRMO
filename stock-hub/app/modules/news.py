from __future__ import annotations

from .. import data
from ..hub import module


def _topic(p):
    out, errors = [], []
    for t in p["topics"]:
        try:
            out.append({"topic": t, "items": data.get_news(t, p.get("limit", 5), p.get("lang", "ja"))})
        except data.DataError as e:
            errors.append(f"{t}: {e}")
    return {"type": "topics", "groups": out, "errors": errors}


# トピックは設定画面/API(params.topics)で自由に増減できる
@module("news.topics", "トピック別ニュース", {"topics": ["AI", "半導体", "金利"], "limit": 5, "lang": "ja"})
def topics(p):
    return _topic(p)
