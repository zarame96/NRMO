# loom100 の出力分布を 公開実証分布(public_reference.json) と突き合わせる検証。
# 逆算でなく「どこが現実と合い・どこがズレているか」を測る。
import sys, json, time, statistics
sys.path.insert(0, "scripts")
import numpy as np
from loom100 import run_century

ref = json.load(open("calibration/public_reference.json", encoding="utf-8"))

# --- (1) バリュエーション式の解析的レンジ vs 実証 ---
def per_of(g, sentiment):
    per = max(5.0, min(55.0, 12.0 + 170.0*max(0.0, g)))   # firm_ifrs _market_cap と同一(較正後)
    return per * sentiment
print("=== (1) PER式 vs 実証 ===")
print(f"  適正 (g=0.02, sent=1.0): {per_of(0.02,1.0):4.0f}x   実証 適正 {ref['valuation_per_x']['fair_range']}x")
print(f"  高成長 (g=0.20, sent=1.0): {per_of(0.20,1.0):4.0f}x")
print(f"  バブル極値 (g=0.43, sent=1.6): {per_of(0.43,1.6):4.0f}x   実証 1989指数極値 {ref['valuation_per_x']['bubble_peak_index_1989']}x")
print(f"  理論最大 (cap55 × sent1.6): {55*1.6:4.0f}x   ← 較正後(個別超高成長の上限)")

# --- (2) モンテカルロ: 生存曲線・営業利益率 ---
N=30; t0=time.time(); years=[]; died=0; margins=[]; causes={}
for seed in range(N):
    rec = run_century(seed, bias_mode="free", engine=None)
    ann = rec.get("annual", [])
    years.append(rec.get("lifespan", len(ann)))
    if rec.get("bankrupt", False):
        died += 1; c=(rec.get("death_reason","") or "?")[:20]; causes[c]=causes.get(c,0)+1
    for a in ann:
        pl=a.get("pl",{}); rev=pl.get("revenue",0.0); op=pl.get("op_income",0.0)
        if rev>0: margins.append(op/rev)
    if time.time()-t0>80: N=seed+1; break
n=len(years)
alive=lambda y: 100.0*sum(1 for x in years if x>=y)/n
print(f"\n=== (2) 生存曲線 (シミュ N={n}) vs 実証(中小企業白書) ===")
for y in (5,10,20,30):
    emp=ref["survival_curve_pct"]["by_year"][str(y)]
    print(f"  {y:2d}年: シミュ {alive(y):5.1f}%  / 実証 ~{emp}%")
print(f"  100年到達 {alive(100):.1f}%  破綻 {died}/{n}")
print(f"\n=== (3) 営業利益率 (シミュ) vs 実証 ===")
if margins:
    print(f"  中央値 {statistics.median(margins)*100:5.1f}%  / 実証 上場全業種~{ref['operating_margin_pct']['listed_all_industry_avg']}%, 製造5.9%, 小売~3-6%")
    print(f"  10-90%tile {np.percentile(margins,10)*100:.1f}% 〜 {np.percentile(margins,90)*100:.1f}%")
print("死因分布:", dict(sorted(causes.items(), key=lambda x:-x[1])))
