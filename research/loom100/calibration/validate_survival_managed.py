# 開放課題への回答: 操舵母集団(NRMO/破滅回避)で生存曲線を再検証し、無操舵と比較。
# 債務系死因が操舵で減るかも見る(=無操舵の債務死支配は操舵の不在による artifact か、真のトリガー過敏か)。
import sys, time, statistics
sys.path.insert(0, "scripts")
import firm_ifrs as F
from loom100 import run_century

REF = {5: 81, 10: 69, 20: 50, 30: 35}   # 中小企業白書(一般企業)

def run_pop(label, bias, managed, N=24, budget=70):
    orig = F.draw_ceo_caliber
    if managed:
        def mc(rng, p=0.0):
            s, t, b, v, r = orig(rng, p)
            return s, t, b, v, min(0.95, max(0.6, r + 0.5))   # 破滅回避を強制的に高める
        F.draw_ceo_caliber = mc
    years = []; causes = {}; t0 = time.time()
    for seed in range(N):
        rec = run_century(seed, bias_mode=bias, engine=None)
        years.append(rec.get("lifespan", len(rec.get("annual", []))))
        if rec.get("bankrupt"):
            c = (rec.get("death_reason", "") or "?")[:18]; causes[c] = causes.get(c, 0) + 1
        if time.time() - t0 > budget: N = seed + 1; break
    if managed: F.draw_ceo_caliber = orig
    n = len(years); alive = lambda y: 100 * sum(1 for x in years if x >= y) / n
    print(f"\n=== {label} (N={n}) ===")
    for y in (5, 10, 20, 30):
        print(f"  {y:2d}年: シミュ {alive(y):5.1f}%  / 実証 ~{REF[y]}%")
    print(f"  100年到達 {alive(100):.1f}%   破綻 {sum(1 for x in years if x < 100)}/{n}   寿命中央値 {statistics.median(years):.0f}年")
    print(f"  死因上位: {dict(sorted(causes.items(), key=lambda x: -x[1])[:4])}")

run_pop("無操舵 (free, ruin_aversion≈0.2)", "free", False)
run_pop("操舵 (conservative + ruin_aversion≥0.6)", "conservative", True)
