# 「20年の壁」を 実StrongEngine Ω Full(現実側・二層) で検証。
# civ-sim探索は重いので n_trials/sim_horizon を抑え、小N＋時間制限（示唆的）。
import sys, time, statistics
sys.path.insert(0, "scripts")
import firm_ifrs as F
from loom100 import run_century
from v7_two_layer import StrongEngineOmegaFull, MaxForwardEngine as CivSim

REF = {5: 81, 10: 69, 20: 50, 30: 35}
def make_eng():
    return StrongEngineOmegaFull(CivSim(n_trials=3, sim_horizon=8))

t0 = time.time()
rec = run_century(0, bias_mode="balanced", engine=make_eng())
print(f"[速度] 1社 {time.time()-t0:.1f}秒  (lifespan {rec.get('lifespan')}年, bankrupt {rec.get('bankrupt')})")

years = [rec.get("lifespan", 0)]; causes = {}
if rec.get("bankrupt"):
    c = (rec.get("death_reason", "") or "?")[:14]; causes[c] = causes.get(c, 0) + 1
budget = 150; t0 = time.time(); seed = 1
while time.time() - t0 < budget and seed < 14:
    rec = run_century(seed, bias_mode="balanced", engine=make_eng())
    years.append(rec.get("lifespan", 0))
    if rec.get("bankrupt"):
        c = (rec.get("death_reason", "") or "?")[:14]; causes[c] = causes.get(c, 0) + 1
    seed += 1
n = len(years); alive = lambda y: 100 * sum(1 for x in years if x >= y) / n
print(f"\n=== 実StrongEngine Ω Full (N={n}, balanced, civ-sim抑制 n_trials3/horizon8) ===")
for y in (5, 10, 20, 30):
    print(f"  {y:2d}年: {alive(y):5.1f}%  (実証 ~{REF[y]}%)")
print(f"  寿命中央 {statistics.median(years):.0f}年   100年到達 {alive(100):.1f}%   破綻 {sum(1 for x in years if x<100)}/{n}")
print(f"  死因: {dict(sorted(causes.items(), key=lambda x: -x[1])[:3])}")
print("  ※ 参考 MaxForwardEngine(前回 balanced): 10年67% / 20年≤12% / 中央12年")
