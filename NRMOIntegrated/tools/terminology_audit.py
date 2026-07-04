#!/usr/bin/env python3
"""terminology_audit.py — 危険表現を検出し置換方針を提示する (P2-4)。"""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
BANNED = {
    "fully proven": "validated in included tests / demonstrated in reference simulation",
    "true dynamics": "domain-native proxy dynamics / implemented domain dynamics",
    "guaranteed survival": "non-ruin filtering in the tested scenarios",
    "complete proof": "reference-simulation evidence",
    "production-ready": "research reference implementation",
    "all systems empirically proven": "validated by the included tests/simulations",
}
SKIP_DIRS = {".git", "archive", "__pycache__"}
# 監査対象は説明文書 (md) と active python の文字列/コメント
EXfile = {"terminology_audit.py", "test_os_boundary_properties.py", "dag_layer.py",
          "RELEASE_CHECKLIST.md", "README.md",
          "run_os_validations.py", "test_dag_layer.py", "test_v8_integrity.py"}  # 検出器/テスト入力/規約記述は除外
hits = []
for p in ROOT.rglob("*"):
    if p.is_dir() or any(s in p.parts for s in SKIP_DIRS):
        continue
    if p.suffix not in (".md", ".py"):
        continue
    if p.name in EXfile:
        continue
    try:
        text = p.read_text(encoding="utf-8", errors="ignore").lower()
    except Exception:
        continue
    for term, repl in BANNED.items():
        if term in text:
            hits.append((str(p.relative_to(ROOT)), term, repl))
print("[TERMINOLOGY AUDIT]")
if not hits:
    print("OK: no banned overclaim terms found in active docs/code"); sys.exit(0)
for f, term, repl in hits:
    print(f"  {f}: '{term}'  ->  '{repl}'")
print(f"FOUND {len(hits)} occurrences (see replacement guidance above)")
sys.exit(1)
