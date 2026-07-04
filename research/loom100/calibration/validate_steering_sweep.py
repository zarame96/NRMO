# 仮説検証: 生存最大の帯は「過保守」でも「無謀」でもなく、破滅縁で操舵する中間(balanced+中ruin_aversion)か。
# loom100内蔵のMaxForwardEngineで bias_mode × ruin_aversion を掃引（外部NRMO-Ωはアダプタ要のため別途）。
import sys, time, statistics
sys.path.insert(0, "scripts")
import firm_ifrs as F
from loom100 import run_century

def run_pop(label, bias, raver_level, N=18, budget=40):
    orig = F.draw_ceo_caliber; patched = False
    if raver_level is not None:
        def mc(rng, p=0.0):
            s, t, b, v, r = orig(rng, p)
            return s, t, b, v, min(0.95, max(0.0, raver_level))
        F.draw_ceo_caliber = mc; patched = True
    years = []; causes = {}; t0 = time.time()
    for seed in range(N):
        rec = run_century(seed, bias_mode=bias, engine=None)
        years.append(rec.get("lifespan", len(rec.get("annual", []))))
        if rec.get("bankrupt"):
            c = (rec.get("death_reason", "") or "?")[:12]; causes[c] = causes.get(c, 0) + 1
        if time.time() - t0 > budget: N = seed + 1; break
    if patched: F.draw_ceo_caliber = orig
    n = len(years); alive = lambda y: 100 * sum(1 for x in years if x >= y) / n
    top = dict(sorted(causes.items(), key=lambda x: -x[1])[:2])
    print(f"{label:34s} 10y {alive(10):5.1f}%  20y {alive(20):5.1f}%  中央{statistics.median(years):4.0f}年  破綻{sum(1 for x in years if x<100):2d}/{n:2d}  {top}")

print(f"{'母集団 (実証 10y~69% / 20y~50%)':34s}")
run_pop("過保守: conservative+raver0.7", "conservative", 0.7)
run_pop("★中間: balanced+raver0.45", "balanced", 0.45)
run_pop("やや前進: balanced+raver0.2", "balanced", 0.2)
run_pop("無謀: aggressive+raver0.1", "aggressive", 0.1)
