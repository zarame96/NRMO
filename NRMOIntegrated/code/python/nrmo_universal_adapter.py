"""
nrmo_universal_adapter.py

NRMO/Loom Universal Adapter Framework.

Per Zarameさん 要望:
  アダプターをいつでも接続できるようにする.
  「これはどうか?あれはどうか?」と聞かれたら、adapter を書くだけで
  Loom/Hybrid を新 domain に適用できる構造.

  Hybrid は有効 → 高出力 proposal + Loom Safety Floor を core engine とする.

Architecture:
  DomainAdapter (ABC)         ← domain ごとに実装 (4 メソッドだけ)
    + propose_high_output()   ← Hybrid 用 高出力 proposal
  NRMOUniversalController     ← 汎用 (Loom 制御 + Safety Floor + Shadow)

新 domain の追加方法:
  1. DomainAdapter を継承
  2. to_loom_state / apply_action / is_ruin / compute_reward を書く
  3. (optional) propose_high_output で Hybrid 化
  4. NRMOUniversalController に渡すだけ
"""
from __future__ import annotations
import os, sys
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Tuple
import numpy as np

LOOM_CORE = os.path.join(os.path.dirname(os.path.abspath(__file__)),"nrmo_v72_phase1","core")
sys.path.insert(0, LOOM_CORE)

from world_models import WorldState as LoomWorldState, Action as LoomAction
from rng_manager import RNGManager
from loom_v3_1 import LoomV31
from sociable_detection_layer import SociableDetectionSystem


# ============================================================
# DomainAdapter — 抽象基底 (新 domain はこれを継承するだけ)
# ============================================================

class DomainAdapter(ABC):
    """新 domain を NRMO/Loom に接続するための adapter base.
    
    必須実装 (4 メソッド):
      to_loom_state    : domain state → 6D WorldState
      apply_action     : Loom action → domain state を更新
      is_ruin          : domain state が破綻状態か
      compute_reward   : 状態遷移の reward
    
    任意実装:
      propose_high_output : Hybrid 用の高出力 proposal
      risk_proximity      : 危機度 (default は R/X から計算)
    """
    
    # Domain メタ情報 (subclass で定義)
    name: str = "unnamed"
    state_semantics: Dict[str, str] = {}   # R/E/G/O/K/X の domain 的意味
    ruin_condition: str = ""                # 破綻条件の説明
    
    @abstractmethod
    def to_loom_state(self, ds: Any) -> LoomWorldState:
        """domain state → Loom 6D WorldState (R,E,G,O,K,X)."""
        ...
    
    @abstractmethod
    def apply_action(self, action: LoomAction, ds: Any, rng) -> Any:
        """Loom action を domain state に適用し、次状態を返す."""
        ...
    
    @abstractmethod
    def is_ruin(self, ds: Any) -> bool:
        """domain state が absorbing failure state か."""
        ...
    
    @abstractmethod
    def compute_reward(self, prev_ds: Any, next_ds: Any) -> float:
        """状態遷移の reward (Loom feedback 用)."""
        ...
    
    # --- optional ---
    
    def propose_high_output(self, ds: Any, rng) -> Optional[LoomAction]:
        """Hybrid 用: 高出力 (aggressive) proposal.
        None を返すと Loom の保守的判断のみ使う.
        default: aggressive invest."""
        return LoomAction("invest", "C")
    
    def risk_proximity(self, ds: Any) -> float:
        """危機度 0-1 (default: R 低 / X 高 で危険)."""
        ls = self.to_loom_state(ds)
        r_part = max(0, (35 - ls.R) / 35.0) * 0.5
        x_part = max(0, (ls.X - 60) / 40.0) * 0.5
        return min(1.0, r_part + x_part)
    
    def describe(self) -> str:
        lines = [f"=== Domain: {self.name} ===",
                  f"  Ruin condition: {self.ruin_condition}",
                  "  State semantics (6D):"]
        for k in ["R", "E", "G", "O", "K", "X"]:
            lines.append(f"    {k} = {self.state_semantics.get(k, '?')}")
        return "\n".join(lines)


# ============================================================
# NRMOUniversalController — 汎用 (Hybrid core)
# ============================================================

class NRMOUniversalController:
    """どの DomainAdapter にも接続できる汎用 NRMO controller.
    
    Hybrid core:
      高出力 proposal (adapter)
        → Loom Control Layer (world detection + risk proximity)
        → Safety Floor (危機時 recover-first)
        → Sociable Shadow (観測 trace)
    """
    
    EMERGENCY_RISK = 0.45  # この危機度以上で Safety Floor 介入
    
    def __init__(self, adapter: DomainAdapter, seed: int = 42,
                  use_hybrid: bool = True,
                  use_safety_floor: bool = True,
                  use_shadow: bool = True):
        self.adapter = adapter
        self.use_hybrid = use_hybrid
        self.use_safety_floor = use_safety_floor
        
        self.loom = LoomV31(rng_manager=RNGManager(master_seed=seed + 900000),
                              use_qs_essence=True)
        self.shadow = SociableDetectionSystem() if use_shadow else None
        
        self.stats = {
            "steps": 0,
            "high_output_used": 0,
            "safety_floor_applied": 0,
            "loom_conservative": 0,
            "shadow_records": 0,
        }
        self._last_action = None
    
    def decide(self, ds: Any, rng) -> LoomAction:
        self.stats["steps"] += 1
        ls = self.adapter.to_loom_state(ds)
        risk = self.adapter.risk_proximity(ds)
        
        # === Hybrid: 危機度で分岐 ===
        if self.use_hybrid and risk < self.EMERGENCY_RISK:
            # 平時: 高出力 proposal を採用
            proposal = self.adapter.propose_high_output(ds, rng)
            if proposal is not None:
                action = proposal
                self.stats["high_output_used"] += 1
                self._last_action = action
                return action
        
        # === 危機時 or Hybrid off: Loom 保守的判断 (Safety Floor 内蔵) ===
        if self.use_safety_floor and risk >= self.EMERGENCY_RISK:
            # Loom の decide (Safety Floor + Sparse Activation が働く)
            decision = self.loom.decide(ls)
            action = decision.action
            self.stats["safety_floor_applied"] += 1
        else:
            decision = self.loom.decide(ls)
            action = decision.action
            self.stats["loom_conservative"] += 1
        
        self._last_action = action
        return action
    
    def observe(self, prev_ds: Any, action: LoomAction, next_ds: Any,
                 reward: float):
        """状態遷移を Loom + Shadow に feedback."""
        ls_prev = self.adapter.to_loom_state(prev_ds)
        ls_next = self.adapter.to_loom_state(next_ds)
        sb = {"R": ls_prev.R, "E": ls_prev.E, "G": ls_prev.G,
              "O": ls_prev.O, "K": ls_prev.K, "X": ls_prev.X}
        sa = {"R": ls_next.R, "E": ls_next.E, "G": ls_next.G,
              "O": ls_next.O, "K": ls_next.K, "X": ls_next.X}
        self.loom.update_reward(action, reward, sb, sa)
        
        # Sociable Shadow (観測のみ)
        if self.shadow is not None:
            world_type = "unknown"
            if self.loom.stats["world_type_counts"]:
                world_type = max(self.loom.stats["world_type_counts"],
                                  key=self.loom.stats["world_type_counts"].get)
            self.shadow.update(
                step=self.stats["steps"], state=ls_prev, action=action,
                module="Hybrid", context_name="domain",
                world_type=world_type, reward=reward,
            )
            self.stats["shadow_records"] += 1
    
    def run_episode(self, init_ds: Any, horizon: int, rng) -> dict:
        """1 episode を回す (adapter.apply_action で transition)."""
        ds = init_ds
        ruined = False
        for step in range(horizon):
            action = self.decide(ds, rng)
            next_ds = self.adapter.apply_action(action, ds, rng)
            reward = self.adapter.compute_reward(ds, next_ds)
            self.observe(ds, action, next_ds, reward)
            ds = next_ds
            if self.adapter.is_ruin(ds):
                ruined = True
                break
        return {"final_state": ds, "ruined": ruined,
                 "survived_steps": step + 1, "stats": dict(self.stats)}


# ============================================================
# Example Adapter 1: 店舗運営 (Zarameさん 本業)
# ============================================================

@dataclass
class StoreState:
    """店舗運営の状態."""
    cash: float = 100.0          # 運転資金
    inventory: float = 50.0      # 在庫水準
    staff_morale: float = 60.0   # スタッフ士気
    customer_base: float = 50.0  # 顧客基盤
    market_knowledge: float = 50.0  # 市場理解
    competitive_pressure: float = 30.0  # 競合圧力
    revenue_accum: float = 0.0
    step: int = 0


class StoreOperationAdapter(DomainAdapter):
    """店舗運営 (retail) を NRMO/Loom に接続."""
    
    name = "店舗運営 (Retail Operation)"
    state_semantics = {
        "R": "運転資金 (cash / liquidity)",
        "E": "事業持続性 (staff morale / sustainability)",
        "G": "オペレーション統治 (operational governance)",
        "O": "選択肢 (顧客基盤の広さ / pivot 余地)",
        "K": "市場理解 (market knowledge)",
        "X": "競合圧力・経営リスク曝露 (competitive/financial exposure)",
    }
    ruin_condition = "運転資金枯渇 (cash < 15) = 倒産"
    
    def to_loom_state(self, ds: StoreState) -> LoomWorldState:
        return LoomWorldState(
            t=ds.step,
            R=float(np.clip(ds.cash, 0, 200) / 2.0),
            E=float(np.clip(ds.staff_morale, 0, 100)),
            G=float(np.clip(100 - abs(ds.inventory - 50), 0, 100)),  # 適正在庫=高G
            O=float(np.clip(ds.customer_base, 0, 100)),
            K=float(np.clip(ds.market_knowledge, 0, 100)),
            X=float(np.clip(ds.competitive_pressure, 0, 100)),
            cumulative_score=ds.revenue_accum,
            is_ruined=(ds.cash < 15),
        )
    
    def apply_action(self, action: LoomAction, ds: StoreState, rng) -> StoreState:
        ns = StoreState(**{k: getattr(ds, k) for k in ds.__dataclass_fields__})
        ns.step = ds.step + 1
        mag = {"A": 0.5, "B": 1.0, "C": 1.5}.get(action.strength, 1.0)
        
        # intent → 経営アクション
        if action.intent == "invest":   # 仕入れ拡大・販促
            ns.inventory += 10 * mag; ns.customer_base += 5 * mag
            ns.cash -= 12 * mag
        elif action.intent == "explore": # 新商品・新規顧客開拓
            ns.market_knowledge += 6 * mag; ns.customer_base += 3 * mag
            ns.cash -= 6 * mag
        elif action.intent == "defend":  # コスト削減・守り
            ns.cash += 3 * mag; ns.competitive_pressure -= 4 * mag
            ns.staff_morale -= 2 * mag
        elif action.intent == "recover": # 立て直し (資金確保優先)
            ns.cash += 8 * mag; ns.inventory -= 5 * mag
            ns.staff_morale += 3 * mag
        # hold: 維持
        
        # Market dynamics
        demand = ns.customer_base * 0.3 * (1 + rng.normal(0, 0.2))
        sales = min(demand, ns.inventory)
        ns.inventory -= sales
        ns.cash += sales * 1.5
        ns.revenue_accum += sales * 1.5
        ns.competitive_pressure += rng.normal(1, 2)
        ns.staff_morale = np.clip(ns.staff_morale + rng.normal(0, 2), 0, 100)
        ns.cash -= 5  # 固定費
        
        for f in ["cash", "inventory", "staff_morale", "customer_base",
                   "market_knowledge", "competitive_pressure"]:
            setattr(ns, f, float(np.clip(getattr(ns, f), 0, 200)))
        return ns
    
    def is_ruin(self, ds: StoreState) -> bool:
        return ds.cash < 15
    
    def compute_reward(self, prev: StoreState, ns: StoreState) -> float:
        return (ns.revenue_accum - prev.revenue_accum) / 20.0 - \
               (0.5 if ns.cash < 30 else 0)
    
    def propose_high_output(self, ds: StoreState, rng) -> LoomAction:
        # 高出力: 資金余裕があれば積極投資
        if ds.cash > 60:
            return LoomAction("invest", "C")
        elif ds.cash > 35:
            return LoomAction("invest", "B")
        return LoomAction("explore", "A")


# ============================================================
# Example Adapter 2: 健康管理
# ============================================================

@dataclass
class HealthState:
    energy: float = 70.0
    fitness: float = 50.0
    habits: float = 50.0
    flexibility: float = 50.0
    health_literacy: float = 50.0
    disease_risk: float = 25.0
    wellbeing_accum: float = 0.0
    step: int = 0


class HealthAdapter(DomainAdapter):
    """健康管理を NRMO/Loom に接続."""
    
    name = "健康管理 (Health Management)"
    state_semantics = {
        "R": "体力・エネルギー (energy reserve)",
        "E": "体調の持続性 (fitness sustainability)",
        "G": "生活習慣の規律 (habit governance)",
        "O": "選択肢 (活動の柔軟性)",
        "K": "健康リテラシー (health literacy)",
        "X": "疾病リスク曝露 (disease risk exposure)",
    }
    ruin_condition = "疾病リスク高騰 (disease_risk > 80) = 健康破綻"
    
    def to_loom_state(self, ds: HealthState) -> LoomWorldState:
        return LoomWorldState(
            t=ds.step, R=ds.energy, E=ds.fitness, G=ds.habits,
            O=ds.flexibility, K=ds.health_literacy, X=ds.disease_risk,
            cumulative_score=ds.wellbeing_accum,
            is_ruined=(ds.disease_risk > 80),
        )
    
    def apply_action(self, action: LoomAction, ds: HealthState, rng) -> HealthState:
        ns = HealthState(**{k: getattr(ds, k) for k in ds.__dataclass_fields__})
        ns.step = ds.step + 1
        mag = {"A": 0.5, "B": 1.0, "C": 1.5}.get(action.strength, 1.0)
        if action.intent == "invest":   # 高強度運動
            ns.fitness += 6*mag; ns.energy -= 8*mag; ns.disease_risk -= 4*mag
        elif action.intent == "explore": # 新習慣・学習
            ns.health_literacy += 6*mag; ns.habits += 3*mag; ns.energy -= 3*mag
        elif action.intent == "defend":  # 休養・予防
            ns.disease_risk -= 5*mag; ns.energy += 4*mag
        elif action.intent == "recover": # 完全休養
            ns.energy += 10*mag; ns.fitness -= 2*mag
        ns.energy = np.clip(ns.energy + rng.normal(0, 3), 0, 100)
        ns.disease_risk = np.clip(ns.disease_risk + rng.normal(0.5, 2)
                                    - ns.fitness*0.02, 0, 100)
        ns.wellbeing_accum += (ns.energy + ns.fitness) / 20.0
        for f in ["energy","fitness","habits","flexibility","health_literacy","disease_risk"]:
            setattr(ns, f, float(np.clip(getattr(ns, f), 0, 100)))
        return ns
    
    def is_ruin(self, ds: HealthState) -> bool:
        return ds.disease_risk > 80
    
    def compute_reward(self, prev: HealthState, ns: HealthState) -> float:
        return (ns.wellbeing_accum - prev.wellbeing_accum) / 10.0 - \
               (0.5 if ns.disease_risk > 60 else 0)
    
    def propose_high_output(self, ds: HealthState, rng) -> LoomAction:
        if ds.energy > 60:
            return LoomAction("invest", "B")  # 運動
        return LoomAction("defend", "A")       # 予防


# ============================================================
# Registry — adapter を名前で登録・取得
# ============================================================

ADAPTER_REGISTRY: Dict[str, type] = {
    "store": StoreOperationAdapter,
    "health": HealthAdapter,
}


def register_adapter(key: str, adapter_cls: type):
    """新 adapter を registry に登録 (いつでも接続可能に)."""
    ADAPTER_REGISTRY[key] = adapter_cls


def make_controller(adapter_key: str, seed: int = 42, **kwargs):
    """registry から adapter を取り、controller を作る."""
    adapter_cls = ADAPTER_REGISTRY[adapter_key]
    return NRMOUniversalController(adapter_cls(), seed=seed, **kwargs)


# ============================================================
# Demo
# ============================================================

if __name__ == "__main__":
    print("=" * 72)
    print("NRMO/Loom Universal Adapter Framework")
    print("  どの domain でも adapter を接続すれば Loom/Hybrid が使える")
    print("=" * 72)
    
    # 登録済み adapter を全て demo
    demos = [
        ("store", StoreState, "店舗運営"),
        ("health", HealthState, "健康管理"),
    ]
    
    for key, StateCls, label in demos:
        adapter_cls = ADAPTER_REGISTRY[key]
        adapter = adapter_cls()
        print(f"\n{adapter.describe()}")
        
        # Hybrid on vs off 比較
        for use_hybrid in [True, False]:
            results = []
            for seed in [42, 123, 777, 2024, 9999]:
                ctrl = NRMOUniversalController(adapter_cls(), seed=seed,
                                                  use_hybrid=use_hybrid)
                rng = np.random.default_rng(seed)
                r = ctrl.run_episode(StateCls(), horizon=150, rng=rng)
                results.append(r)
            
            ruin_rate = np.mean([r["ruined"] for r in results])
            surv = np.mean([r["survived_steps"] for r in results])
            final_scores = [r["final_state"].revenue_accum if key=="store"
                             else r["final_state"].wellbeing_accum for r in results]
            avg_score = np.mean(final_scores)
            tag = "Hybrid" if use_hybrid else "Loom単体"
            print(f"    [{tag:<8}] score={avg_score:7.1f}, "
                  f"ruin_rate={ruin_rate:.0%}, survival={surv:.0f}/150")
    
    print("\n" + "=" * 72)
    print("新 domain の追加方法:")
    print("  1. DomainAdapter を継承し to_loom_state/apply_action/")
    print("     is_ruin/compute_reward を実装")
    print("  2. propose_high_output で Hybrid 化 (任意)")
    print("  3. register_adapter('key', YourAdapter) で登録")
    print("  → 以降いつでも make_controller('key') で接続可能")
    print("=" * 72)
    print("\n[Universal Adapter Framework 動作確認 ✅]")
