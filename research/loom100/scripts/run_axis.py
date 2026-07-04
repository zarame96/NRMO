import sys,time,json; sys.path.insert(0,"scripts"); sys.path.insert(0,".")
import firm_ifrs as Fm, loom100 as L
import numpy as np, statistics as st
M=Fm.M; BUDGET=90; t0=time.time()
res={}
for mode in ["conservative","balanced","aggressive","free"]:
    life=[]; teq=[]; cause={}; surv20=0; n=0
    for i in range(16):
        if time.time()-t0>BUDGET: break
        r=L.run_century(i*7+3, bias_mode=mode); n+=1
        life.append(r["lifespan"]); teq.append(r["final_equity"]/M)
        if r["lifespan"]>=20: surv20+=1
        if r["bankrupt"]: cause[r["death_reason"][:6]]=cause.get(r["death_reason"][:6],0)+1
    sv=[e for e,l in zip(teq,life) if l>=20]
    res[mode]=dict(n=n, med=st.median(life), mean=float(np.mean(life)), mx=max(life),
                   surv20=surv20/max(1,n), sv_eq=(st.median(sv) if sv else None),
                   cause=max(cause,key=cause.get) if cause else "-")
json.dump(res, open("/tmp/axis.json","w"), ensure_ascii=False)
print(f"完了 {time.time()-t0:.0f}秒")
for m,d in res.items():
    print(f"{m:<13} n={d['n']:>2} 中央寿命{d['med']:>4.0f}年 平均{d['mean']:>4.0f}年 最長{d['mx']:>3.0f}年 "
          f"生存20年{d['surv20']:>4.0%} 生存純資産中央={(d['sv_eq'] or 0):>6.0f}M 主死因={d['cause']}")
