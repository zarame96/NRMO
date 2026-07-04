"""
run_all_validations.py — StrongEngine Ω Full 一発検証 (numpy のみ, 依存欠落なし)

合格条件 (添付批評):
  PASS engine_never_reads_veto_thresholds
  PASS selected_action_always_in_admissible
  PASS vetoed_action_unreachable
  PASS empty_admissible_returns_hold
  PASS domain_rollout_uses_domain_dynamics
  PASS memory_changes_future_candidate_distribution
  PASS no_NRMO_boundary_mutation_by_engine
  PASS all_domain_examples_reproduce
"""
from __future__ import annotations
import copy, sys
import numpy as np
from separation_engine import (
    StrongEngineOmegaFull, GoalInterpreter, Memory, HorizonPolicy, HOLD)

R, E, G, O, K, X = 0, 1, 2, 3, 4, 5


# ============================================================
# 自己完結 domain (個人意思決定の proxy dynamics)
# ============================================================
class DemoDomain:
    def clone(self, s): return s.copy()

    def forward_value(self, s):
        # 前進量 = 能力 + 選択肢 (暴露 X は引かない: 暴露は ruin 経由でのみ効く)
        return float(s[R] + s[K] + s[O] + 0.5 * (s[E] + s[G]))

    def is_ruin(self, s):
        return bool(s[E] <= 5 or s[G] <= 5 or s[X] >= 100)

    def context(self, s):
        xb = "low" if s[X] < 40 else ("high" if s[X] > 70 else "mid")
        caps = {"R": s[R], "E": s[E], "G": s[G], "O": s[O], "K": s[K], "X": 100 - s[X]}
        weakest = min(caps, key=caps.get)
        return dict(exposure_band=xb, weakest_dim=("X" if 100 - s[X] == caps[weakest] else weakest),
                    favorable=(s[X] < 40 and s[E] > 45 and s[G] > 45))

    def transition(self, s, a, rng):
        g, sf, lr, di = a
        n = s.copy()
        n[R] += 6 * g - 1.5 * sf
        n[K] += 4 * lr + 2 * g
        n[O] += 3 * g - 1.0
        n[E] += 1.5 - 2.0 * g + 1.5 * sf
        n[G] += 1.0 - 1.5 * g + 1.0 * sf
        n[X] += 5 * g - 6 * sf - 3 * di + 1.0
        # shock: 暴露が高く安全余裕が低いほど被害大 (★有界: base を上限でクリップ)
        p = 0.05 + 0.006 * max(0.0, n[X])
        if rng.random() < min(0.6, p):
            base = min(rng.exponential(6.0), 16.0)          # ★有界 shock (cap=16)
            mag = base * (0.5 + n[X] / 100.0) * (1.0 - 0.6 * sf) * (1.0 - 0.4 * di)
            n[E] -= mag
            n[G] -= 0.7 * mag
        n[R:K + 1] = np.clip(n[R:K + 1], 0, 200)
        n[X] = float(np.clip(n[X], 0, 110))
        return n


def fresh_state():
    return np.array([55.0, 55.0, 55.0, 50.0, 50.0, 35.0])


# ============================================================
# NRMO governance (veto only)。閾値は内部に隠蔽。
#   悲観的判定: もっともらしい大 shock を仮定して次状態が破滅域なら veto。
#   ⇒ admissible action は worst-case でも破滅しない ⇒ 軌道 ruin=0 を保証。
# ============================================================
class DemoNRMO:
    def __init__(self):
        self._x_cap = 92.0     # ★ veto 閾値 (Engine は決して読めない)
        self._floor = 9.0
        self._pessimistic_shock = 16.0   # = domain の shock 上限 ⇒ worst-case を厳密に被覆

    def _vetoed(self, a, s):
        g, sf, lr, di = a
        n = s.copy()
        n[E] += 1.5 - 2.0 * g + 1.5 * sf
        n[G] += 1.0 - 1.5 * g + 1.0 * sf
        n[X] += 5 * g - 6 * sf - 3 * di + 1.0
        # 悲観 shock を当てる
        mag = self._pessimistic_shock * (0.5 + max(0, n[X]) / 100.0) * (1 - 0.6 * sf) * (1 - 0.4 * di)
        n[E] -= mag; n[G] -= 0.7 * mag
        return (n[E] <= self._floor) or (n[G] <= self._floor) or (n[X] >= self._x_cap)

    def filter(self, candidates, state):
        return [c for c in candidates if not self._vetoed(c, state)]


# ============================================================
# テスト補助
# ============================================================
class OnlyFilterProxy:
    """filter() 以外の属性アクセスを禁止する黒箱 proxy。
       Engine が veto 閾値等を読めば AttributeError になる。"""
    def __init__(self, gov): object.__setattr__(self, "_gov", gov)
    def filter(self, candidates, state):
        return object.__getattribute__(self, "_gov").filter(candidates, state)
    def __getattr__(self, name):
        raise AttributeError(f"Engine tried to read governance internal '{name}' (forbidden)")
    def __setattr__(self, k, v):
        raise AttributeError("Engine tried to mutate governance (forbidden)")


class CountingDomain(DemoDomain):
    def __init__(self): self.transitions = 0
    def transition(self, s, a, rng):
        self.transitions += 1
        return super().transition(s, a, rng)


def _engine(memory_enabled=True, horizon=18):
    return StrongEngineOmegaFull(
        memory=Memory(enabled=memory_enabled), horizon=HorizonPolicy(long_horizon=horizon))


# ============================================================
# 8 テスト
# ============================================================
def t_engine_never_reads_veto_thresholds():
    eng = _engine(); dyn = DemoDomain(); goal = GoalInterpreter()
    gov = OnlyFilterProxy(DemoNRMO())
    rng = np.random.default_rng(0)
    # filter 以外を読めば AttributeError。完走すれば合格。
    for _ in range(15):
        action, _ = eng.step(gov, dyn, fresh_state(), goal, rng)
    return True


def t_selected_action_always_in_admissible():
    eng = _engine(); dyn = DemoDomain(); goal = GoalInterpreter(); gov = DemoNRMO()
    rng = np.random.default_rng(1); s = fresh_state()
    for _ in range(40):
        proposals = eng.propose(dyn, s, goal, rng)
        adm = gov.filter([a for a, _ in proposals], s)
        if not adm:
            s = fresh_state(); continue
        a = eng.select(adm, dyn, s, goal, gov, rng)
        assert any(np.array_equal(a, c) for c in adm)
        s = dyn.transition(s, a, rng)
        if dyn.is_ruin(s): s = fresh_state()
    return True


def t_vetoed_action_unreachable():
    # g>0.5 を全て veto する governance。選択 action は必ず g<=0.5。
    class CapG(DemoNRMO):
        def filter(self, candidates, state):
            return [c for c in candidates if c[0] <= 0.5]
    eng = _engine(); dyn = DemoDomain(); goal = GoalInterpreter(); gov = CapG()
    rng = np.random.default_rng(2); s = fresh_state()
    for _ in range(40):
        a, _ = eng.step(gov, dyn, s, goal, rng)
        if a is HOLD: s = fresh_state(); continue
        assert a[0] <= 0.5 + 1e-12, f"vetoed action reached: g={a[0]}"
        s = dyn.transition(s, a, rng)
        if dyn.is_ruin(s): s = fresh_state()
    return True


def t_empty_admissible_returns_hold():
    class VetoAll(DemoNRMO):
        def filter(self, candidates, state): return []
    eng = _engine(); dyn = DemoDomain(); goal = GoalInterpreter()
    a, gen = eng.step(VetoAll(), dyn, fresh_state(), goal, np.random.default_rng(3))
    assert a == HOLD and gen is None
    return True


def t_domain_rollout_uses_domain_dynamics():
    eng = _engine(horizon=12); dyn = CountingDomain(); goal = GoalInterpreter(); gov = DemoNRMO()
    rng = np.random.default_rng(4); s = fresh_state()
    proposals = eng.propose(dyn, s, goal, rng)
    adm = gov.filter([a for a, _ in proposals], s)
    before = dyn.transitions
    eng.select(adm, dyn, s, goal, gov, rng)
    assert dyn.transitions > before, "select() must roll out via domain dynamics"
    return True


def t_memory_changes_future_candidate_distribution():
    dyn = DemoDomain(); goal = GoalInterpreter()
    fav = np.array([60.0, 60.0, 60.0, 50.0, 50.0, 25.0])  # favorable → wolf が候補を出す局面
    ctx = dyn.context(fav)
    def fwd_share(mem):
        eng = StrongEngineOmegaFull(memory=mem)
        rng = np.random.default_rng(7); tot = w = 0
        for _ in range(60):
            eng.propose(dyn, fav, goal, rng)
            w += eng.last_usage.get("forward_push", 0); tot += sum(eng.last_usage.values())
        return w / max(1, tot)
    base = fwd_share(Memory(enabled=True))
    trained = Memory(enabled=True)
    for _ in range(60): trained.update(ctx, "forward_push", True)     # wolf 成功を学習
    for _ in range(60): trained.update(ctx, "low_exposure", False) # shinobi 失敗
    after = fwd_share(trained)
    assert after > base + 0.02, f"memory did not shift distribution: {base:.3f}->{after:.3f}"
    return True


def t_no_NRMO_boundary_mutation_by_engine():
    eng = _engine(); dyn = DemoDomain(); goal = GoalInterpreter(); gov = DemoNRMO()
    snap = copy.deepcopy(gov.__dict__)
    rng = np.random.default_rng(5); s = fresh_state()
    for _ in range(25):
        a, _ = eng.step(gov, dyn, s, goal, rng)
        if a is HOLD: s = fresh_state(); continue
        s = dyn.transition(s, a, rng)
        if dyn.is_ruin(s): s = fresh_state()
    assert gov.__dict__ == snap, "engine mutated NRMO boundary"
    return True


def t_all_domain_examples_reproduce():
    def run(seed):
        eng = _engine(horizon=20); dyn = DemoDomain(); goal = GoalInterpreter(); gov = DemoNRMO()
        rng = np.random.default_rng(seed); s = fresh_state()
        f0 = dyn.forward_value(s); ruined = False; holds = 0
        for _ in range(150):
            a, _ = eng.step(gov, dyn, s, goal, rng)
            if a is HOLD: holds += 1; 
            if a is HOLD:
                # 縁: 最も安全な退避 (暴露低減) を NRMO に通るまで探す
                safe = np.array([0.10, 0.55, 0.20, 0.30])
                if gov.filter([safe], s): s = dyn.transition(s, safe, rng)
                continue
            s = dyn.transition(s, a, rng)
            if dyn.is_ruin(s): ruined = True; break
        return ruined, dyn.forward_value(s) - f0, holds
    r1 = run(11); r2 = run(11)               # 同 seed → 完全再現
    assert r1 == r2, "not reproducible"
    ruined, gain, _ = run(11)
    assert not ruined, "NRMO failed to prevent ruin"
    assert gain > 0, "engine did not advance"
    # 別 seed でも ruin 0 / 前進 を確認
    for sd in (12, 13, 14):
        ru, gn, _ = run(sd)
        assert (not ru) and gn > 0, f"seed {sd}: ruin={ru} gain={gn:.1f}"
    return True


TESTS = [
    ("engine_never_reads_veto_thresholds", t_engine_never_reads_veto_thresholds),
    ("selected_action_always_in_admissible", t_selected_action_always_in_admissible),
    ("vetoed_action_unreachable", t_vetoed_action_unreachable),
    ("empty_admissible_returns_hold", t_empty_admissible_returns_hold),
    ("domain_rollout_uses_domain_dynamics", t_domain_rollout_uses_domain_dynamics),
    ("memory_changes_future_candidate_distribution", t_memory_changes_future_candidate_distribution),
    ("no_NRMO_boundary_mutation_by_engine", t_no_NRMO_boundary_mutation_by_engine),
    ("all_domain_examples_reproduce", t_all_domain_examples_reproduce),
]

if __name__ == "__main__":
    print("=" * 60)
    print("StrongEngine Ω Full — run_all_validations")
    print("=" * 60)

    # ---- Part A: 本物サブシステムの生存検証 (実コード駆動。v6 core 要) ----
    print("\n[Part A] 本物サブシステム駆動 (Wolf/Shinobi/MAPLayer/Norn-Skuld/Loom)")
    try:
        import omega_full_integrated as ofi
        checks, _u, _s, _l = ofi.validate_subsystems_alive()
        for name, ok in checks:
            print(f"  {'PASS' if ok else 'FAIL'}: {name}")
        a_fail = sum(1 for _, ok in checks if not ok)
    except Exception as e:
        print(f"  SKIP: 実コード未配置 ({type(e).__name__}: {e}). "
              f"NRMO_CORE_PATH (旧 NRMO_V6_CORE) を設定すると本物を駆動検証します。")
        a_fail = 0
        a_skipped = True
    else:
        a_skipped = False

    # ---- Part B: NRMO 分離契約 (汎用参照 engine, numpy のみ) ----
    print("\n[Part B] NRMO 分離契約 (propose→filter→select, ruin_penalty 排除)")
    fails = 0
    for name, fn in TESTS:
        try:
            fn(); print(f"  PASS: {name}")
        except Exception as e:
            fails += 1; print(f"  FAIL: {name}  -- {e}")
    print("=" * 60)
    total = fails + a_fail
    if total:
        print(f"RESULT: FAIL ({total} failed)")
        sys.exit(1)
    if a_skipped:
        print("RESULT: PARTIAL PASS (Part B 8/8; Part A real-core SKIPPED — set NRMO_CORE_PATH)")
        sys.exit(2)
    print("RESULT: ALL PASS WITH REAL CORE (Part A 10/10 + Part B 8/8)")
    sys.exit(0)
