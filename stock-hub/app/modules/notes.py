"""ノート: 話した/書いた内容を貯め、Claudeで「事業の種」を抽出する。"""
from __future__ import annotations

import json
import os
import time

import httpx

from .. import hub
from ..hub import module

MODEL = os.environ.get("STOCK_HUB_MODEL", "claude-sonnet-5-5")


def _path():
    return hub.DATA_DIR / "notes.json"


def load_notes() -> list[dict]:
    try:
        return json.loads(_path().read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def add_note(text: str) -> dict:
    text = text.strip()
    if not text or len(text) > 20000:
        raise ValueError("text must be 1..20000 chars")
    with hub._lock:
        notes = load_notes()
        n = {"id": int(time.time() * 1000), "ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "text": text}
        notes.append(n)
        hub.DATA_DIR.mkdir(parents=True, exist_ok=True)
        _path().write_text(json.dumps(notes, ensure_ascii=False, indent=1))
    return n


SYSTEM = (
    "あなたは起業の壁打ち相手。ユーザーのメモ群から『事業の種』を最大5つ抽出する。"
    "繰り返し現れる不満・得意・関心を重視し、各案に: title, 誰が困っているか, 何にお金を払いそうか, "
    "根拠となったメモ引用, 最小の検証方法(1週間・低コスト), リスク を日本語のJSON配列で返す。"
    "推測と事実を区別し、根拠が薄いものは confidence=low とする。JSON以外は出力しない。"
)


def extract_seeds(limit: int = 50) -> list[dict]:
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise RuntimeError("ANTHROPIC_API_KEY が未設定です")
    notes = load_notes()[-limit:]
    if not notes:
        return []
    body = "\n".join(f"[{n['ts']}] {n['text']}" for n in notes)
    r = httpx.post(
        "https://api.anthropic.com/v1/messages",
        headers={"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
        json={"model": MODEL, "max_tokens": 2000, "system": SYSTEM,
              "messages": [{"role": "user", "content": body}]},
        timeout=60,
    )
    r.raise_for_status()
    text = r.json()["content"][0]["text"].strip()
    text = text.removeprefix("```json").removesuffix("```").strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return [{"title": "(解析不能)", "raw": text}]


@module("notes.memo", "メモと事業の種", {"show": 20})
def memo(p):
    ns = load_notes()[-p["show"]:][::-1]
    return {"type": "notes", "items": ns}
