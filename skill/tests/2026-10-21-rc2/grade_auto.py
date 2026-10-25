"""機械的に判定できる観点だけを抽出する。意味の判定（許容集合と候補の整合、採用範囲）は人が読む。"""
import json, re, sys, glob, os

def load(path):
    calls, result, skills = [], None, []
    for line in open(path, encoding="utf-8"):
        try:
            ev = json.loads(line)
        except Exception:
            continue
        if ev.get("type") == "system" and ev.get("subtype") == "init":
            skills = [s for s in ev.get("skills", []) if "nrmo" in str(s)]
        if ev.get("type") == "assistant":
            for c in ev.get("message", {}).get("content", []):
                if c.get("type") == "tool_use":
                    inp = c.get("input", {})
                    calls.append((c["name"], str(inp.get("skill") or inp.get("file_path") or inp.get("pattern") or inp.get("command") or inp.get("query") or "")[:200]))
        if ev.get("type") == "result":
            result = ev
    return skills, calls, result

def type_zero_line(text):
    for ln in text.splitlines():
        if "Type ZERO" in ln or "Type Zero" in ln:
            return ln.strip()
    return None

rows = []
d = sys.argv[1]
for p in sorted(glob.glob(os.path.join(d, "*_r?.jsonl"))):
    rid = os.path.basename(p)[:-6]
    skills, calls, res = load(p)
    out = (res or {}).get("result") or ""
    invoked = any(n == "Skill" for n, _ in calls)
    read_canon = any(n == "Read" and "nrmo_system_v7_3.md" in a for n, a in calls)
    rows.append({
        "run": rid,
        "skill_loaded_in_session": skills,
        "skill_invoked": invoked,
        "read_canon": read_canon,
        "tool_calls": calls,
        "type_zero_line": type_zero_line(out),
        "type_zero_undetermined": ("未判定" in (type_zero_line(out) or "")),
        "nrmo_vocab_hits": [w for w in ["A_allowed", "Type ZERO", "Operational", "Passive Ruin", "Active Ruin", "HOLD", "破綻境界"] if w in out],
        "is_error": (res or {}).get("is_error"),
        "num_turns": (res or {}).get("num_turns"),
        "duration_ms": (res or {}).get("duration_ms"),
        "permission_denials": [x.get("tool_name") for x in (res or {}).get("permission_denials", [])],
    })
    with open(os.path.join(d, rid + ".output.md"), "w", encoding="utf-8") as f:
        f.write(f"# {rid}\n\n## ツール履歴\n\n")
        for n, a in calls:
            f.write(f"- {n}: `{a}`\n")
        f.write("\n## 出力全文\n\n")
        f.write(out)
        f.write("\n")
json.dump(rows, open(os.path.join(d, "auto_checks.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
for r in rows:
    print(r["run"], "invoked=" + str(r["skill_invoked"]), "canon=" + str(r["read_canon"]), "TZ=" + str(r["type_zero_line"])[:90], "deny=" + str(r["permission_denials"]))
