import sys,time,json; sys.path.insert(0,"scripts"); sys.path.insert(0,".")
import importlib, firm_ifrs as Fm, loom100 as L; importlib.reload(Fm); importlib.reload(L)
M=Fm.M; BUDGET=95; t0=time.time(); best=None; n=0
for seed in range(70):
    if time.time()-t0>BUDGET: break
    r=L.run_century(seed); n+=1
    if best is None or r["lifespan"]>best["lifespan"]: best=r
def clean(r):
    eras=[]
    for e in r["eras"]:
        e=dict(e); e["regimes"]=sorted(e["regimes"])
        for k in ("min_equity","max_equity"): e[k]=float(e[k])/M
        eras.append(e)
    return dict(seed=int(r["seed"]), hostility=round(float(r["hostility"]),3),
                lifespan=float(r["lifespan"]), bankrupt=bool(r["bankrupt"]),
                death_reason=r["death_reason"], generations=int(r["generations"]),
                final_equity=float(r["final_equity"])/M, peak_equity=float(r["peak_equity"])/M,
                annual=[{**{k:(round(float(v)/M,2) if k in("pl","bs") else v) for k,v in a.items() if k not in("pl","bs")},
                         "pl":{k:round(float(v)/M,2) for k,v in a["pl"].items()},
                         "bs":{k:round(float(v)/M,2) for k,v in a["bs"].items()}} for a in r["annual"]],
                eras=eras, crises=r["crises"])
json.dump(clean(best), open("/tmp/best_record.json","w"), ensure_ascii=False)
print(f"探索{n}社 {time.time()-t0:.0f}秒 / 最長寿 seed={best['seed']} 寿命{best['lifespan']:.0f}年 第{best['generations']}代 "
      f"年次{len(best['annual'])}期 危機{len(best['crises'])}回 ピーク純資産{best['peak_equity']/M:.0f}M 死因={best['death_reason'] or '生存'}")
