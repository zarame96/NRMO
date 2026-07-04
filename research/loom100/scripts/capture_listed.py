import sys,time,json; sys.path.insert(0,"scripts"); sys.path.insert(0,".")
import importlib, firm_ifrs as Fm, loom100 as L; importlib.reload(Fm); importlib.reload(L)
M=Fm.M; t0=time.time(); chosen=None; longest=None
for seed in range(24):
    if time.time()-t0>95: break
    r=L.run_century(seed)
    if longest is None or r["lifespan"]>longest["lifespan"]: longest=r
    if r["lifespan"]>=100 and r["final"].listed:     # 100年生存かつ上場
        chosen=r; break
r=chosen or longest
s=r["final"]
def clean(r):
    eras=[]
    for e in r["eras"]:
        e=dict(e); e["regimes"]=sorted(e["regimes"])
        e["min_equity"]=float(e["min_equity"])/M; e["max_equity"]=float(e["max_equity"])/M
        eras.append(e)
    annual=[]
    for a in r["annual"]:
        annual.append({**{k:v for k,v in a.items() if k not in("pl","bs")},
                       "pl":{k:round(float(v)/M,2) for k,v in a["pl"].items()},
                       "bs":{k:round(float(v)/M,2) for k,v in a["bs"].items()}})
    return dict(seed=int(r["seed"]),hostility=round(float(r["hostility"]),3),lifespan=float(r["lifespan"]),
                bankrupt=bool(r["bankrupt"]),death_reason=r["death_reason"],generations=int(r["generations"]),
                listed=bool(s.listed), final_equity=round(float(r["final_equity"])/M,1),
                peak_equity=round(float(r["peak_equity"])/M,1), annual=annual, eras=eras, crises=r["crises"])
rec=clean(r); json.dump(rec, open("/tmp/listed_record.json","w"), ensure_ascii=False)
# IPO年を特定
ipo_year=next((a["year"] for a in r["annual"] if a["bs"]["share"]>r["annual"][0]["bs"]["share"]*1.5), None)
print(f"代表企業 seed={rec['seed']} 寿命{rec['lifespan']:.0f}年 上場={rec['listed']} 第{rec['generations']}代 "
      f"危機{len(rec['crises'])}回 ピーク純資産{rec['peak_equity']:.0f}M 死因={rec['death_reason'] or '生存(100年)'}")
print(f"年次三表 {len(rec['annual'])}期, 貸借不一致 {sum(1 for a in r['annual'] if abs(a['check'])>1)}件")
print(f"資本金: {rec['annual'][0]['bs']['share']:.0f}M → {rec['annual'][-1]['bs']['share']:.0f}M (増資/IPOで増加, IPO頃={ipo_year}年)")
print("代別の判断軸と帰結:")
for e in rec["eras"]:
    if e.get("end_year",0)-e["start_year"]<1 and e["gen"]>1: continue
    am=max(e["actions"],key=e["actions"].get) if e["actions"] else "-"
    print(f"  第{e['gen']}代 {L.bias_label(e['bias'])}({e['bias']:+.2f}) {e['start_year']:.0f}→{e.get('end_year',0):.0f}年 "
          f"純資産{e.get('end_equity',0):>6}M 危機{e['crises']}回 主手={am}")
