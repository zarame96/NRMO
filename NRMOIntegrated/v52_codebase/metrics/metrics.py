"""
metrics/metrics.py — Aggregation, ruin analysis, composite scoring
"""
from __future__ import annotations
import pandas as pd
from typing import List
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from simulation.simulator import EpisodeResult
from config.defaults import ScoreWeights

def results_to_df(results:List[EpisodeResult])->pd.DataFrame:
    return pd.DataFrame([{
        "world":r.world_name,"strategy":r.strategy_name,"run_id":r.run_id,"seed":r.seed,
        "lifespan":r.lifespan,"alive":r.alive,"true_ruin":r.true_ruin,"passive_ruin":r.passive_ruin,
        "ruin_type":r.ruin_type,"ruin_step":r.ruin_step,
        "final_R":r.final_R,"final_E":r.final_E,"final_G":r.final_G,
        "final_O":r.final_O,"final_K":r.final_K,"final_X":r.final_X,
        "cum_prod":r.cum_prod,"peak_prod":r.peak_prod,"peak_X":r.peak_X,"mean_prod":r.mean_prod,
        "selected_profile":r.selected_profile,"profile_switch_count":r.profile_switch_count,
    } for r in results])

def _agg(g):
    return pd.Series({
        "n":len(g),"survival_rate":g["alive"].mean(),"true_ruin_rate":g["true_ruin"].mean(),
        "passive_ruin_rate":g["passive_ruin"].mean(),"mean_lifespan":g["lifespan"].mean(),
        "median_lifespan":g["lifespan"].median(),"mean_final_R":g["final_R"].mean(),
        "mean_final_E":g["final_E"].mean(),"mean_final_G":g["final_G"].mean(),
        "mean_final_O":g["final_O"].mean(),"mean_final_K":g["final_K"].mean(),
        "mean_final_X":g["final_X"].mean(),"mean_peak_X":g["peak_X"].mean(),
        "mean_cum_prod":g["cum_prod"].mean(),"mean_prod":g["mean_prod"].mean(),
        "mean_switches":g["profile_switch_count"].mean(),
    })

def aggregate_world(df): return df.groupby(["world","strategy"]).apply(_agg,include_groups=False).reset_index()
def aggregate_overall(df): return df.groupby("strategy").apply(_agg,include_groups=False).reset_index()

def compute_score(r, w=ScoreWeights()):
    return (w.survival_rate*r["survival_rate"]+w.true_ruin_rate*r["true_ruin_rate"]
            +w.passive_ruin_rate*r["passive_ruin_rate"]
            +w.optionality*(r["mean_final_O"]/130)+w.productivity*(r["mean_cum_prod"]/200)
            +w.exposure*(r["mean_final_X"]/130))

def add_scores(df, w=ScoreWeights()):
    df=df.copy(); df["score"]=df.apply(lambda r:compute_score(r,w),axis=1); return df

def ruin_analysis(df):
    ruined=df[df["ruin_type"]!="alive"]
    if ruined.empty: return pd.DataFrame()
    c=ruined.groupby(["world","strategy","ruin_type"]).size().reset_index(name="count")
    t=ruined.groupby(["world","strategy"]).size().reset_index(name="total")
    m=c.merge(t,on=["world","strategy"]); m["pct"]=(m["count"]/m["total"]*100).round(1)
    st=ruined.groupby(["world","strategy","ruin_type"])["ruin_step"].mean().reset_index(name="mean_step")
    m=m.merge(st,on=["world","strategy","ruin_type"]); m["mean_step"]=m["mean_step"].round(1)
    return m.sort_values(["world","strategy","count"],ascending=[True,True,False])

def ruin_summary(df):
    ruined=df[df["ruin_type"]!="alive"]
    if ruined.empty: return pd.DataFrame()
    c=ruined.groupby(["strategy","ruin_type"]).size().reset_index(name="count")
    t=ruined.groupby("strategy").size().reset_index(name="total")
    m=c.merge(t,on="strategy"); m["pct"]=(m["count"]/m["total"]*100).round(1)
    return m.sort_values(["strategy","count"],ascending=[True,False])

def export_all(raw,wagg,oagg,d="."):
    raw.to_csv(f"{d}/raw_simulation.csv",index=False)
    wagg.to_csv(f"{d}/world_results.csv",index=False)
    oagg.to_csv(f"{d}/overall_results.csv",index=False)
    ra=ruin_analysis(raw); rs=ruin_summary(raw)
    if not ra.empty: ra.to_csv(f"{d}/ruin_analysis.csv",index=False)
    if not rs.empty: rs.to_csv(f"{d}/ruin_summary.csv",index=False)
    print(f"CSVs → {d}/")
