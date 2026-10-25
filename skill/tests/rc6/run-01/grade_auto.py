"""機械的に判定できる観点だけを抽出する（rc2 の grade_auto.py を rc3 用に調整）。意味の判定は人が読む。"""
import json, sys, glob, os

def load(path):
    calls, result, skills, init = [], None, [], {}
    for line in open(path, encoding="utf-8"):
        try:
            ev = json.loads(line)
        except Exception:
            continue
        if ev.get("type") == "system" and ev.get("subtype") == "init":
            init = ev
            skills = [s for s in ev.get("skills", []) if "nrmo" in str(s)]
        if ev.get("type") == "assistant":
            for c in ev.get("message", {}).get("content", []):
                if c.get("type") == "tool_use":
                    inp = c.get("input", {})
                    calls.append((c["name"], str(inp.get("skill") or inp.get("file_path") or inp.get("pattern") or inp.get("query") or "")[:200]))
        if ev.get("type") == "result":
            result = ev
    return init, skills, calls, result

def tz_line(text):
    for ln in text.splitlines():
        if "Type ZERO" in ln or "Type Zero" in ln:
            return ln.strip()
    return None

d = sys.argv[1]
rows = []
for p in sorted(glob.glob(os.path.join(d, "raw", "*_r?.jsonl"))):
    rid = os.path.basename(p)[:-6]
    init, skills, calls, res = load(p)
    mp = os.path.join(d, "meta", rid + ".json")
    if not os.path.exists(mp):
        continue
    meta = json.load(open(mp))
    out = (res or {}).get("result") or ""
    rows.append({
        "run": rid,
        "exit_code": meta["exit_code"],
        "prompt_sha256": meta["prompt_sha256"],
        "model": init.get("model"),
        "cli_version": init.get("claude_code_version"),
        "tools_available": init.get("tools"),
        "nrmo_skills_in_session": skills,
        "mcp_servers": init.get("mcp_servers"),
        "skill_invoked": any(n == "Skill" for n, _ in calls),
        "read_canon": any(n == "Read" and "nrmo_system_v7_3.md" in a for n, a in calls),
        "tool_calls": calls,
        "type_zero_line": tz_line(out),
        "is_error": (res or {}).get("is_error"),
        "num_turns": (res or {}).get("num_turns"),
        "duration_ms": (res or {}).get("duration_ms"),
        "permission_denials": [x.get("tool_name") for x in (res or {}).get("permission_denials", [])],
    })
    os.makedirs(os.path.join(d, "outputs"), exist_ok=True)
    with open(os.path.join(d, "outputs", rid + ".output.md"), "w", encoding="utf-8") as f:
        f.write(f"# {rid}\n\n## 入力\n\n{open(os.path.join(d, 'input', rid + '.txt'), encoding='utf-8').read()}\n\n## ツール履歴\n\n")
        for n, a in calls:
            f.write(f"- {n}: `{a}`\n")
        f.write("\n## 出力全文\n\n" + out + "\n")
json.dump(rows, open(os.path.join(d, "auto_checks.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
for r in rows:
    print(r["run"], "ec=%s" % r["exit_code"], "err=%s" % r["is_error"], "skills=%s" % r["nrmo_skills_in_session"], "invoked=%s" % r["skill_invoked"], "canon=%s" % r["read_canon"], "deny=%s" % r["permission_denials"], "TZ=" + str(r["type_zero_line"])[:80])
