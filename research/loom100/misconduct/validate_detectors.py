# loom100 の崩壊前 firm-year を 検出指標(Beneish/Altman/継続企業) が捉えるか検証。
# 逆算でなく『崩壊前 vs 平時』で指標が差を出すかを測る。
import sys, time, statistics
sys.path.insert(0, "scripts"); sys.path.insert(0, "misconduct")
from loom100 import run_century
from distress_detectors import beneish_m_score, altman_z, going_concern_flags

N=24; t0=time.time()
pre_Z=[]; base_Z=[]; pre_M=[]; base_M=[]; pre_gc=0; pre_yrs=0; base_gc=0; base_yrs=0
keys_printed=False
for seed in range(N):
    rec=run_century(seed, bias_mode="free", engine=None)
    ann=rec.get("annual",[]); n=len(ann); bankrupt=rec.get("bankrupt",False)
    if not keys_printed and ann:
        print("pl keys:", sorted(ann[0]["pl"].keys()))
        print("bs keys:", sorted(ann[0]["bs"].keys())); keys_printed=True
    for i,y in enumerate(ann):
        if y["pl"].get("revenue",0)<=0: continue
        pre = bankrupt and i >= n-3            # 破綻3年前以内
        mc = (y.get("share_price",0)*y.get("shares",0)) if y.get("listed") else None
        z = altman_z(y, market_cap=mc)["Z"]
        gc = len(going_concern_flags(y))>0
        (pre_Z if pre else base_Z).append(z)
        if pre: pre_yrs+=1; pre_gc+=1 if gc else 0
        else:   base_yrs+=1; base_gc+=1 if gc else 0
        if i>=1 and ann[i-1]["pl"].get("revenue",0)>0:
            m=beneish_m_score(ann[i-1], y)["M"]; (pre_M if pre else base_M).append(m)
    if time.time()-t0>80: N=seed+1; break

def pctl(v,thr,lt=True): 
    if not v: return float("nan")
    return 100.0*sum(1 for x in v if (x<thr if lt else x>thr))/len(v)
print(f"\n=== 検証 (loom100 {N}社, engine=None) ===")
print(f"Altman Z  危険(<1.81)割合:  崩壊前 {pctl(pre_Z,1.81):.0f}%  / 平時 {pctl(base_Z,1.81):.0f}%")
print(f"          中央値:           崩壊前 {statistics.median(pre_Z) if pre_Z else float('nan'):.2f}  / 平時 {statistics.median(base_Z) if base_Z else float('nan'):.2f}")
print(f"Beneish M 操作疑い(>-2.22)割合: 崩壊前 {pctl(pre_M,-2.22,lt=False):.0f}%  / 平時 {pctl(base_M,-2.22,lt=False):.0f}%")
print(f"          中央値:           崩壊前 {statistics.median(pre_M) if pre_M else float('nan'):.2f}  / 平時 {statistics.median(base_M) if base_M else float('nan'):.2f}")
print(f"継続企業の赤信号あり割合:    崩壊前 {100*pre_gc/max(1,pre_yrs):.0f}%  / 平時 {100*base_gc/max(1,base_yrs):.0f}%")
print(f"(サンプル firm-years: 崩壊前 {pre_yrs}, 平時 {base_yrs})")
