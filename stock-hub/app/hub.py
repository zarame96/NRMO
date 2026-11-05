"""統合環境のコア: モジュール登録・設定の永続化・ツリー生成。

モジュール追加 = modules/ に1ファイル足して @module を付けるだけ。
画面のON/OFF・並べ替え・パラメータは data/config.json に保存される。
"""
from __future__ import annotations

import json
import os
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

DATA_DIR = Path(os.environ.get("STOCK_HUB_DATA", Path(__file__).resolve().parent.parent / "data"))
CONFIG_PATH = DATA_DIR / "config.json"
_lock = threading.Lock()

# カテゴリ表示名(ID先頭要素 → 表示名)。未登録ならIDをそのまま表示。
CATEGORIES = {"finance": "金融", "news": "ニュース", "net": "ネット", "notes": "ノート"}


@dataclass
class Module:
    id: str                      # 例 "finance.stock"
    title: str
    fetch: Callable[[dict], dict]
    params: dict = field(default_factory=dict)   # 既定パラメータ
    enabled: bool = True


REGISTRY: dict[str, Module] = {}


def module(id: str, title: str, params: dict | None = None, enabled: bool = True):
    def deco(fn):
        REGISTRY[id] = Module(id, title, fn, params or {}, enabled)
        return fn
    return deco


def _load() -> dict:
    try:
        return json.loads(CONFIG_PATH.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save(cfg: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    tmp = CONFIG_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(cfg, ensure_ascii=False, indent=2))
    tmp.replace(CONFIG_PATH)


def effective(mid: str) -> dict:
    m = REGISTRY[mid]
    c = _load().get(mid, {})
    return {
        "enabled": c.get("enabled", m.enabled),
        "order": c.get("order", list(REGISTRY).index(mid)),
        "params": {**m.params, **c.get("params", {})},
    }


def update(mid: str, patch: dict) -> dict:
    if mid not in REGISTRY:
        raise KeyError(mid)
    allowed = {k: v for k, v in patch.items() if k in ("enabled", "order", "params")}
    if "enabled" in allowed and not isinstance(allowed["enabled"], bool):
        raise ValueError("enabled must be bool")
    if "order" in allowed and not isinstance(allowed["order"], int):
        raise ValueError("order must be int")
    if "params" in allowed and not isinstance(allowed["params"], dict):
        raise ValueError("params must be object")
    with _lock:
        cfg = _load()
        cfg.setdefault(mid, {}).update(allowed)
        _save(cfg)
    return effective(mid)


def tree() -> list[dict]:
    """カテゴリ > モジュール のツリー(order順)。無効モジュールも返す(画面でON/OFFするため)。"""
    cats: dict[str, list[dict]] = {}
    for mid, m in REGISTRY.items():
        e = effective(mid)
        cats.setdefault(mid.split(".")[0], []).append({"id": mid, "title": m.title, **e})
    return [
        {"id": c, "title": CATEGORIES.get(c, c), "modules": sorted(ms, key=lambda x: x["order"])}
        for c, ms in cats.items()
    ]


def run(mid: str) -> dict:
    if mid not in REGISTRY:
        raise KeyError(mid)
    e = effective(mid)
    if not e["enabled"]:
        return {"type": "message", "text": "このモジュールは無効です"}
    return REGISTRY[mid].fetch(e["params"])
