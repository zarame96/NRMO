import sys,time; sys.path.insert(0,"scripts"); sys.path.insert(0,".")
import importlib, firm_ifrs as Fm; importlib.reload(Fm)
import numpy as np, statistics as st
M=Fm.M; eng=Fm.MaxForwardEngine(); t0=time.time()
bad=0; checked=0; life=[]; r100=0; listed_cnt=0; teq=[]; causes={}; n=0
for seed in range(40):
    if time.time()-t0>95: break
    rng=np.random.default_rng(seed); host=float(rng.beta(2,3))
    dyn=Fm.FirmDynamicsIFRS(predatory=True,hostility=host); s=Fm.IFRSFirmState(); ly=0; n+=1
    for q in range(400):
        a=eng.decide(dyn,s,rng); s=dyn.transition(s,a,rng); ly=(q+1)/4
        if abs(s.total_assets-(s.total_liabilities+s.equity))>1: bad+=1
        checked+=1
        if s.bankrupt: break
    life.append(ly if s.bankrupt else 100.0); teq.append(s.equity/M)
    if not s.bankrupt: r100+=1
    if s.listed: listed_cnt+=1
    if s.bankrupt: causes[s.death_reason[:12]]=causes.get(s.death_reason[:12],0)+1
print(f"検証 {n}社 {time.time()-t0:.0f}秒")
print(f"貸借不一致 {bad}/{checked}期 → {'OK 恒等式維持' if bad==0 else 'NG'}")
print(f"100年到達 {r100}/{n}={r100/n:.0%}  寿命中央={st.median(life):.0f}年 平均={np.mean(life):.0f} 最長={max(life):.0f}")
sv=[e for e,l in zip(teq,life) if l>=100]
print(f"上場到達 {listed_cnt}/{n}={listed_cnt/n:.0%}  100年生存企業の純資産中央={st.median(sv) if sv else float('nan'):.0f}M")
print(f"死因: {causes}")
