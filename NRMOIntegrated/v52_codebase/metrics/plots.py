"""
metrics/plots.py — 8 chart visualization suite
"""
from __future__ import annotations
import numpy as np, pandas as pd, matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path

SORDER=["ExpectedValueMax","RiskAdjustedUtility","UltraConservative",
    "NRMO_Original","NRMO_vNext","AlphaSearch","NRMO_StrongEngine",
    "NRMOvNext_StrongEngine","Adaptive_NRMOvNext_SE","Adaptive_NRMOvNext_OmegaFull"]
SHORT={"ExpectedValueMax":"EV-Max","RiskAdjustedUtility":"Risk-Adj","UltraConservative":"Ultra-Con",
    "NRMO_Original":"NRMO","NRMO_vNext":"vNext","AlphaSearch":"Alpha",
    "NRMO_StrongEngine":"NRMO+SE","NRMOvNext_StrongEngine":"vNext+SE",
    "Adaptive_NRMOvNext_SE":"Adapt+SE","Adaptive_NRMOvNext_OmegaFull":"Ω-Full"}
PAL=["#e74c3c","#e67e22","#95a5a6","#3498db","#2980b9","#9b59b6","#1abc9c","#16a085","#27ae60","#2c3e50"]

def _s(n): return SHORT.get(n,n)
def _ord(df,c="strategy"):
    cats=[s for s in SORDER if s in df[c].values]; df=df[df[c].isin(cats)].copy()
    df[c]=pd.Categorical(df[c],categories=cats,ordered=True); return df.sort_values(c)
def _sv(fig,p): fig.savefig(p,dpi=180,bbox_inches="tight",facecolor="white"); plt.close(fig); print(f"  → {p}")

def plot_performance(ov,d):
    df=_ord(ov); fig,ax=plt.subplots(figsize=(14,5)); x=np.arange(len(df))
    bars=ax.bar(x,df["score"],color=PAL[:len(df)],edgecolor="white",lw=.5)
    ax.set_xticks(x); ax.set_xticklabels([_s(s) for s in df["strategy"]],rotation=35,ha="right")
    ax.set_ylabel("Score"); ax.set_title("Overall Performance",fontsize=13,fontweight="bold"); ax.axhline(0,color="grey",lw=.5)
    for b,v in zip(bars,df["score"]): ax.text(b.get_x()+b.get_width()/2,b.get_height()+.005,f"{v:.3f}",ha="center",fontsize=7)
    fig.tight_layout(); _sv(fig,f"{d}/performance_comparison.png")

def plot_survival(wa,d):
    df=_ord(wa); ws=sorted(df["world"].unique()); ss=df["strategy"].cat.categories.tolist()
    ns,nw=len(ss),len(ws); fig,ax=plt.subplots(figsize=(15,5)); w=.8/ns
    for i,st in enumerate(ss):
        sub=df[df["strategy"]==st].set_index("world")
        v=[sub.loc[ww,"survival_rate"] if ww in sub.index else 0 for ww in ws]
        ax.bar(np.arange(nw)+i*w,v,width=w,label=_s(st),color=PAL[i%len(PAL)],edgecolor="white",lw=.3)
    ax.set_xticks(np.arange(nw)+w*ns/2-w/2); ax.set_xticklabels(ws,fontsize=9)
    ax.set_ylabel("Survival Rate"); ax.set_ylim(0,1.05); ax.set_title("Survival by World",fontsize=13,fontweight="bold")
    ax.legend(fontsize=6,ncol=3,loc="lower right"); fig.tight_layout(); _sv(fig,f"{d}/survival_by_world.png")

def plot_exp_prod(wa,d):
    df=_ord(wa); ss=df["strategy"].cat.categories.tolist(); fig,ax=plt.subplots(figsize=(9,7))
    for i,st in enumerate(ss):
        sub=df[df["strategy"]==st]
        ax.scatter(sub["mean_peak_X"],sub["mean_cum_prod"],color=PAL[i%len(PAL)],label=_s(st),s=65,alpha=.85,edgecolors="white",lw=.5)
    ax.set_xlabel("Mean Peak Exposure"); ax.set_ylabel("Mean Cumulative Prod")
    ax.set_title("Exposure vs Productivity",fontsize=13,fontweight="bold"); ax.legend(fontsize=7); fig.tight_layout(); _sv(fig,f"{d}/exposure_vs_productivity.png")

def plot_opt(raw,d):
    df=_ord(raw); ss=df["strategy"].cat.categories.tolist(); fig,ax=plt.subplots(figsize=(14,5))
    bp=ax.boxplot([df[df["strategy"]==s]["final_O"].values for s in ss],labels=[_s(s) for s in ss],patch_artist=True,showfliers=False)
    for p,c in zip(bp["boxes"],PAL[:len(ss)]): p.set_facecolor(c); p.set_alpha(.6)
    ax.set_ylabel("Final Optionality"); ax.set_title("Optionality Distribution",fontsize=13,fontweight="bold")
    plt.xticks(rotation=35,ha="right"); fig.tight_layout(); _sv(fig,f"{d}/optionality_distribution.png")

def plot_ruin(ov,d):
    df=_ord(ov); fig,ax=plt.subplots(figsize=(14,5)); x=np.arange(len(df)); w=.35
    ax.bar(x-w/2,df["true_ruin_rate"],w,label="True Ruin",color="#e74c3c",edgecolor="white")
    ax.bar(x+w/2,df["passive_ruin_rate"],w,label="Passive Ruin",color="#f39c12",edgecolor="white")
    ax.set_xticks(x); ax.set_xticklabels([_s(s) for s in df["strategy"]],rotation=35,ha="right")
    ax.set_ylabel("Rate"); ax.set_title("Ruin Rates",fontsize=13,fontweight="bold"); ax.legend(); fig.tight_layout(); _sv(fig,f"{d}/ruin_rates.png")

def plot_lifespan(raw,d):
    df=_ord(raw); ss=df["strategy"].cat.categories.tolist(); fig,ax=plt.subplots(figsize=(14,5))
    bp=ax.boxplot([df[df["strategy"]==s]["lifespan"].values for s in ss],labels=[_s(s) for s in ss],patch_artist=True,showfliers=False)
    for p,c in zip(bp["boxes"],PAL[:len(ss)]): p.set_facecolor(c); p.set_alpha(.6)
    ax.set_ylabel("Lifespan"); ax.set_title("Lifespan Distribution",fontsize=13,fontweight="bold")
    plt.xticks(rotation=35,ha="right"); fig.tight_layout(); _sv(fig,f"{d}/lifespan_distribution.png")

def plot_ruin_causes(raw,d):
    ruined=raw[raw["ruin_type"]!="alive"].copy()
    if ruined.empty: return
    top=ruined["ruin_type"].value_counts().head(7).index.tolist(); ruined=ruined[ruined["ruin_type"].isin(top)]
    ct=pd.crosstab(ruined["strategy"],ruined["ruin_type"])
    ordered=[s for s in SORDER if s in ct.index]; ct=ct.reindex(ordered); ct=ct.div(ct.sum(axis=1),axis=0)
    fig,ax=plt.subplots(figsize=(14,5)); ct.plot.bar(stacked=True,ax=ax,colormap="tab10",edgecolor="white",lw=.3)
    ax.set_xticklabels([_s(s) for s in ct.index],rotation=35,ha="right"); ax.set_ylabel("Proportion")
    ax.set_title("Ruin Cause Breakdown",fontsize=13,fontweight="bold"); ax.legend(fontsize=6); fig.tight_layout(); _sv(fig,f"{d}/ruin_cause_breakdown.png")

def plot_heatmap(wa,d):
    df=_ord(wa); pv=df.pivot_table(index="strategy",columns="world",values="survival_rate")
    ordered=[s for s in SORDER if s in pv.index]; pv=pv.reindex(ordered)
    fig,ax=plt.subplots(figsize=(11,7)); im=ax.imshow(pv.values,cmap="RdYlGn",aspect="auto",vmin=0,vmax=1)
    ax.set_xticks(range(len(pv.columns))); ax.set_xticklabels(pv.columns,rotation=30,ha="right",fontsize=9)
    ax.set_yticks(range(len(pv.index))); ax.set_yticklabels([_s(s) for s in pv.index],fontsize=9)
    for i in range(len(pv.index)):
        for j in range(len(pv.columns)):
            v=pv.values[i,j]; ax.text(j,i,f"{v:.0%}",ha="center",va="center",fontsize=8,color="black" if v>.4 else "white")
    fig.colorbar(im,ax=ax,label="Survival Rate"); ax.set_title("Survival Heatmap",fontsize=13,fontweight="bold")
    fig.tight_layout(); _sv(fig,f"{d}/survival_heatmap.png")

def generate_all_plots(raw,wa,ov,d="."):
    Path(d).mkdir(parents=True,exist_ok=True); print("Generating plots...")
    plot_performance(ov,d); plot_survival(wa,d); plot_exp_prod(wa,d); plot_opt(raw,d)
    plot_ruin(ov,d); plot_lifespan(raw,d); plot_ruin_causes(raw,d); plot_heatmap(wa,d)
    print("All plots done.")
