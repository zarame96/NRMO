import json, sys, pathlib

def extract(path):
    calls, final, init = [], None, None
    for line in pathlib.Path(path).read_text(encoding="utf-8").splitlines():
        try:
            ev = json.loads(line)
        except Exception:
            continue
        t = ev.get("type")
        if t == "system" and ev.get("subtype") == "init":
            init = {"model": ev.get("model"), "cwd": ev.get("cwd"),
                    "skills": [s for s in ev.get("skills", []) if "nrmo" in str(s)],
                    "tools": ev.get("tools")}
        if t == "assistant":
            for c in ev.get("message", {}).get("content", []):
                if c.get("type") == "tool_use":
                    inp = c.get("input", {})
                    brief = inp.get("skill") or inp.get("file_path") or inp.get("pattern") or inp.get("command") or ""
                    calls.append(f'{c["name"]}: {str(brief)[:160]}')
        if t == "result":
            final = {"result": ev.get("result"), "is_error": ev.get("is_error"),
                     "num_turns": ev.get("num_turns"), "duration_ms": ev.get("duration_ms"),
                     "cost": ev.get("total_cost_usd")}
    return init, calls, final

if __name__ == "__main__":
    for p in sys.argv[1:]:
        init, calls, final = extract(p)
        print("=" * 70)
        print(p)
        print("init:", json.dumps(init, ensure_ascii=False)[:600] if init else None)
        print("tool calls:")
        for c in calls:
            print("  -", c)
        if final:
            print("meta:", {k: v for k, v in final.items() if k != "result"})
            print("----- FINAL OUTPUT -----")
            print(final["result"])
        else:
            print("(no result event yet)")
