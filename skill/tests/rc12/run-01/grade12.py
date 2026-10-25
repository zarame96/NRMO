"""rc12: 機械的に抽出できる観点（init、ツール呼び出し、PDF の Read と pages、結果のエラー）だけを出す。意味の判定は人が読む。"""
import json, sys, glob, os, re

REQ = {"§60.3": {465}, "§63.1": {471}, "§63.2": {472}, "§64.1": {473}, "§64.2": {473, 474},
       "ch3": set(range(61, 72)), "caged(PDF ch22 / tex)": set(range(211, 217))}

def pages_of(spec):
    out = set()
    for part in str(spec or "").split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            a, b = part.split("-", 1)
            out |= set(range(int(a), int(b) + 1))
        elif part.isdigit():
            out.add(int(part))
    return out

def load(path):
    init, calls, res, results = {}, [], None, {}
    for line in open(path, encoding="utf-8"):
        try:
            ev = json.loads(line)
        except Exception:
            continue
        if ev.get("type") == "system" and ev.get("subtype") == "init":
            init = ev
        if ev.get("type") == "assistant":
            for c in ev.get("message", {}).get("content", []):
                if c.get("type") == "tool_use":
                    calls.append({"id": c["id"], "name": c["name"], "input": c.get("input", {})})
        if ev.get("type") == "user":
            content = ev.get("message", {}).get("content", [])
            if isinstance(content, list):
                for c in content:
                    if isinstance(c, dict) and c.get("type") == "tool_result":
                        txt = c.get("content")
                        if isinstance(txt, list):
                            txt = " ".join(x.get("text", "") if isinstance(x, dict) and x.get("type") == "text" else f"[{x.get('type')}]" for x in txt)
                        results[c.get("tool_use_id")] = {"is_error": bool(c.get("is_error")), "head": str(txt)[:300], "full": str(txt)}
        if ev.get("type") == "result":
            res = ev
    return init, calls, res, results

d = sys.argv[1]
rows = []
for p in sorted(glob.glob(os.path.join(d, "raw", "*_r*.jsonl"))):
    rid = os.path.basename(p)[:-6]
    mp = os.path.join(d, "meta", rid + ".json")
    if not os.path.exists(mp):
        continue
    meta = json.load(open(mp))
    init, calls, res, results = load(p)
    out = (res or {}).get("result") or ""
    pdf_ok, pdf_reads = set(), []
    for c in calls:
        fp = str(c["input"].get("file_path", ""))
        if c["name"] == "Read" and fp.endswith(".pdf"):
            r = results.get(c["id"], {})
            pg = pages_of(c["input"].get("pages"))
            pdf_reads.append({"pages": c["input"].get("pages"), "is_error": r.get("is_error"), "result_head": r.get("head", "")[:160]})
            if not r.get("is_error") and r:
                pdf_ok |= pg
        r = results.get(c["id"], {})
        if c["name"] == "Read" and fp.endswith("ch20_caged_beast.tex") and r and not r.get("is_error"):
            pdf_ok |= {"tex20"}
        gp = str(c["input"].get("path", ""))
        if (c["name"] == "Grep" and gp.endswith("ch20_caged_beast.tex") and c["input"].get("pattern")
                and c["input"].get("output_mode") == "content" and r and not r.get("is_error")
                and re.search(r"(^|\n)\d+[:-]", r.get("full", ""))):
            pdf_ok |= {"tex20"}
    access = {k: bool(v & pdf_ok) if k != "§64.2" else v <= pdf_ok for k, v in REQ.items()}
    access["caged(PDF ch22 / tex)"] = access["caged(PDF ch22 / tex)"] or "tex20" in pdf_ok
    single = any(x["pages"] and not x["is_error"] and pages_of(x["pages"]) >= set(range(463, 475)) and "," not in str(x["pages"]) for x in pdf_reads)
    read_files = [os.path.relpath(str(c["input"].get("file_path")), "/") for c in calls if c["name"] == "Read"]
    rows.append({
        "run": rid, "exit_code": meta["exit_code"], "prompt_sha256": meta["prompt_sha256"],
        "model": init.get("model"), "cli_version": init.get("claude_code_version"),
        "skills": [s for s in init.get("skills", []) if "nrmo" in str(s)], "mcp_servers": init.get("mcp_servers"),
        "skill_invoked": any(c["name"] == "Skill" for c in calls),
        "reads": [ (c["name"], str(c["input"].get("file_path") or c["input"].get("pattern") or c["input"].get("skill") or "")[-90:], c["input"].get("pages"), results.get(c["id"], {}).get("is_error")) for c in calls],
        "pdf_reads": pdf_reads, "pdf_access": access, "single_range_463_474": single,
        "is_error": (res or {}).get("is_error"), "num_turns": (res or {}).get("num_turns"),
        "permission_denials": [x.get("tool_name") for x in (res or {}).get("permission_denials", [])],
    })
    os.makedirs(os.path.join(d, "outputs"), exist_ok=True)
    with open(os.path.join(d, "outputs", rid + ".output.md"), "w", encoding="utf-8") as f:
        f.write(f"# {rid}\n\n## 入力\n\n{open(os.path.join(d, 'input', rid + '.txt'), encoding='utf-8').read()}\n\n## ツール履歴\n\n")
        for c in calls:
            r = results.get(c["id"], {})
            f.write(f"- {c['name']}: `{c['input'].get('file_path') or c['input'].get('pattern') or c['input'].get('skill') or ''}`"
                    + (f" pages={c['input'].get('pages')}" if c['input'].get('pages') else "")
                    + (" **ERROR**" if r.get("is_error") else "") + "\n")
        f.write("\n## 出力全文\n\n" + out + "\n")
json.dump(rows, open(os.path.join(d, "auto_checks.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
for r in rows:
    acc = "".join("1" if r["pdf_access"][k] else "." for k in REQ)
    print(r["run"], "ec=%s" % r["exit_code"], "inv=%s" % r["skill_invoked"], "pdfreads=%s" % [(x["pages"], x["is_error"]) for x in r["pdf_reads"]], "acc[603,631,632,641,642,ch3,caged]=" + acc, "single=%s" % r["single_range_463_474"])
