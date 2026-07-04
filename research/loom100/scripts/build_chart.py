# -*- coding: utf-8 -*-
"""純資産・株価の推移 + 制度イベント(IPO/業態転換/世代交代/監査否認)を描く。"""
import json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm

FP="/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
jp=fm.FontProperties(fname=FP)
plt.rcParams["axes.unicode_minus"]=False

C=json.load(open("/tmp/century_full.json",encoding="utf-8"))
Y=json.load(open("/tmp/young_full.json",encoding="utf-8"))
M=1_000_000

def years(r):   return [a["year"] for a in r["annual"]]
def equity(r):  return [a["bs"]["equity"]/M for a in r["annual"]]
def price(r):   return [a.get("share_price",0) for a in r["annual"]]
def listed_years(r): return [a["year"] for a in r["annual"] if a.get("listed")]

fig=plt.figure(figsize=(13,9)); 
gs=fig.add_gridspec(2,1,height_ratios=[2.4,1.0],hspace=0.55)

# ===== 上: 代表企業 =====
ax=fig.add_subplot(gs[0]); ax2=ax.twinx()
yr=years(C); eq=equity(C)
ax.plot(yr, eq, color="#1B5E9B", lw=2.6, marker="o", ms=4, label="純資産(百万円)", zorder=3)
ax.axhline(0, color="#999", lw=1, ls="--")
ax.fill_between(yr, eq, 0, where=[e>=0 for e in eq], color="#1B5E9B", alpha=0.10)
ax.fill_between(yr, eq, 0, where=[e<0 for e in eq], color="#C0392B", alpha=0.18)

# 株価(上場期間のみ右軸)
ly=listed_years(C)
if ly:
    lp=[a.get("share_price",0) for a in C["annual"] if a.get("listed")]
    ax2.plot(ly, [p/M for p in lp], color="#E67E22", lw=2.4, marker="s", ms=5, label="株価(百万円/株)", zorder=4)
    ax2.set_ylabel("株価（百万円/株, 上場期間）", fontproperties=jp, color="#E67E22")
    ax2.tick_params(axis="y", colors="#E67E22")

# 世代交代の縦線
gens=set()
for a in C["annual"]:
    g=a["gen"]
    if g not in gens:
        gens.add(g)
        if g>1: ax.axvline(a["year"], color="#7F8C8D", lw=1, ls=":", alpha=0.8)

# 制度イベント(eraのevents)からマーカー
import re
ev_styles={"IPO":("#27AE60","IPO上場"),"業態転換":("#8E44AD","業態転換"),"監査意見":("#C0392B","監査否認"),
           "新規事業":("#2980B9","新規事業"),"上場廃止":("#E74C3C","上場廃止"),"配当開始":("#16A085","配当開始")}
seen=set()
for e in C["eras"]:
    for txt in e["events"]:
        m=re.match(r"(\d+)年\s*(\S+)", txt)
        if not m: continue
        yy=int(m.group(1))
        for key,(col,lab) in ev_styles.items():
            if key in txt:
                yv=eq[min(len(eq)-1, max(0,yy-1))]
                ax.annotate(lab, xy=(yy,yv), xytext=(yy, yv+max(eq)*0.10),
                            fontproperties=jp, fontsize=8, color=col, ha="center",
                            arrowprops=dict(arrowstyle="->", color=col, lw=1.2))
                break

ax.set_title(f"代表企業（seed{C['seed']}）: 純資産と株価の推移 — {C['lifespan']:.0f}年 / 第{C.get('generations',1)}代 / {C['market'].upper()}・{C['accounting'].upper()}",
             fontproperties=jp, fontsize=13, color="#1B2748", pad=12)
ax.set_xlabel("経過年", fontproperties=jp); ax.set_ylabel("純資産（百万円）", fontproperties=jp, color="#1B5E9B")
ax.tick_params(axis="y", colors="#1B5E9B")
ax.grid(True, alpha=0.25)
l1,la1=ax.get_legend_handles_labels(); l2,la2=ax2.get_legend_handles_labels()
ax.legend(l1+l2, la1+la2, prop=jp, loc="upper left", framealpha=0.9)

# 理念バナー
fig.text(0.5,0.015,f"企業理念『{C.get('creed','')}』 最終 理念整合度={C.get('creed_align',1.0):.2f}　業態転換{C.get('pivot_count',0)}回・新規事業{C.get('new_biz_count',0)}件・チャネル{C.get('final_channels','-')}・内製化{C.get('final_insourcing',0):.0%}",
        ha="center", va="bottom", fontproperties=jp, fontsize=9, color="#555")

# ===== 下: 対照(零細) =====
axy=fig.add_subplot(gs[1])
yry=years(Y); eqy=equity(Y)
axy.plot(yry, eqy, color="#7F8C8D", lw=2.2, marker="o", ms=3)
axy.fill_between(yry, eqy, 0, color="#7F8C8D", alpha=0.12)
axy.axhline(0, color="#999", lw=1, ls="--")
axy.scatter([yry[-1]],[eqy[-1]], color="#C0392B", s=70, zorder=5, label="破綻")
axy.set_title(f"対照: 未上場の零細企業（seed{Y['seed']}）— {Y['lifespan']:.0f}年で破綻（資本市場アクセス無し）",
              fontproperties=jp, fontsize=11, color="#1B2748")
axy.set_xlabel("経過年", fontproperties=jp); axy.set_ylabel("純資産（百万円）", fontproperties=jp)
axy.grid(True, alpha=0.25); axy.legend(prop=jp, loc="upper right")

fig.savefig("/mnt/user-data/outputs/NRMO_100年_純資産推移.png", dpi=140, bbox_inches="tight")
print("chart 作成")
