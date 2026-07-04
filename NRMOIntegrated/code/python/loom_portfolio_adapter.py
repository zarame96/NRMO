"""
loom_portfolio_adapter.py

NRMO/Loom を金融ポートフォリオ意思決定に適用する demo.

civ-sim でやったのと同じ adapter pattern:
  PortfolioState (6D) ⇄ Loom WorldState
  Loom Action (intent/strength) → allocation (equity/cash/explore/rebalance)
  ruin = catastrophic drawdown

これは「シミュレーション以外」への汎用性の実証.
NRMO の核心 (破綻境界を守りながら reachability を維持) が
portfolio management に直接適用できることを示す.

注: market data は synthetic (regime-switching GBM + crash) で生成.
real data 不要で再現可能.
"""
from __future__ import annotations
import os, sys
import numpy as np
from dataclasses import dataclass

LOOM_CORE = os.path.join(os.path.dirname(os.path.abspath(__file__)),"nrmo_v72_phase1","core")
sys.path.insert(0, LOOM_CORE)

from world_models import WorldState as LoomWorldState, Action as LoomAction
from rng_manager import RNGManager
from loom_v3_1 import LoomV31


# ============================================================
# Portfolio State (domain)
# ============================================================

@dataclass
class PortfolioState:
    """ポートフォリオの状態."""
    value: float = 100.0        # 現在の総資産 (初期 100)
    peak_value: float = 100.0   # 過去最高値 (drawdown 計算用)
    cash_ratio: float = 0.5     # 現金比率 (0-1)
    equity_ratio: float = 0.5   # 株式比率 (0-1)
    realized_vol: float = 0.15  # 直近の実現ボラティリティ
    trend_strength: float = 0.0 # トレンド強度 (-1 to 1)
    step: int = 0
    ruined: bool = False
    
    @property
    def drawdown(self) -> float:
        if self.peak_value <= 0:
            return 0.0
        return max(0.0, (self.peak_value - self.value) / self.peak_value)


# ============================================================
# Portfolio Adapter (civ-sim の LoomCivAdapter と同じ思想)
# ============================================================

class PortfolioAdapter:
    """PortfolioState ⇄ Loom WorldState, Loom Action → allocation."""
    
    RUIN_DRAWDOWN = 0.40  # 40% drawdown = 回復困難 (ruin)
    
    @staticmethod
    def portfolio_to_loom(ps: PortfolioState) -> LoomWorldState:
        """PortfolioState → Loom 6D WorldState.
        
        R = 資産水準 (cash buffer 含む流動性)      → 高いほど安全
        E = portfolio health (リターンの持続性)
        G = 分散度 (リスク統治)
        O = optionality (rebalance 余地 = cash)
        K = 市場知識 (trend confidence)
        X = drawdown/volatility 曝露              → 高いほど危険
        """
        # 0-100 scale に map
        R = float(np.clip(ps.value, 0, 200) / 2.0)  # value 100 → R 50
        E = float(np.clip(100 * (1 - ps.realized_vol * 2), 0, 100))  # 低 vol = 高 E
        G = float(np.clip(100 * (1 - abs(ps.equity_ratio - 0.5) * 2), 0, 100))  # 分散
        O = float(np.clip(ps.cash_ratio * 100, 0, 100))  # cash = optionality
        K = float(np.clip(50 + ps.trend_strength * 50, 0, 100))  # trend
        X = float(np.clip(ps.drawdown * 150 + ps.realized_vol * 100, 0, 100))  # 曝露
        
        return LoomWorldState(
            t=ps.step, R=R, E=E, G=G, O=O, K=K, X=X,
            cumulative_score=ps.value - 100.0,
            is_ruined=ps.ruined,
        )
    
    @staticmethod
    def loom_action_to_allocation(action: LoomAction,
                                     current: PortfolioState) -> float:
        """Loom Action → target equity ratio (0-1).
        
        intent:
          invest  → equity 増 (risk-on)
          explore → equity やや増 (新規 position)
          hold    → 維持
          defend  → cash 増 (risk-off)
          recover → cash 大幅増 (de-risk)
        strength A/B/C → 変更幅
        """
        delta_map = {
            "invest":  +0.20,
            "explore": +0.10,
            "hold":     0.00,
            "defend":  -0.20,
            "recover": -0.35,
        }
        mag = {"A": 0.5, "B": 1.0, "C": 1.5}.get(action.strength, 1.0)
        delta = delta_map.get(action.intent, 0.0) * mag
        
        target_equity = float(np.clip(current.equity_ratio + delta, 0.0, 1.0))
        return target_equity


# ============================================================
# Synthetic Market (regime-switching, with crashes)
# ============================================================

class SyntheticMarket:
    """Regime-switching market: bull / bear / crash.
    
    real data 不要で再現可能な market simulator.
    """
    
    def __init__(self, seed: int = 42):
        self.rng = np.random.default_rng(seed)
        self.regime = "bull"
        self.regime_steps = 0
    
    def step(self) -> tuple:
        """1 step の market return (equity_return, vol) を返す."""
        # Regime transition
        self.regime_steps += 1
        if self.regime == "bull":
            if self.rng.random() < 0.04 or self.regime_steps > 40:
                self.regime = self.rng.choice(["bear", "crash"], p=[0.8, 0.2])
                self.regime_steps = 0
        elif self.regime == "bear":
            if self.rng.random() < 0.08 or self.regime_steps > 20:
                self.regime = "bull"
                self.regime_steps = 0
        elif self.regime == "crash":
            if self.rng.random() < 0.30:
                self.regime = "bear"
                self.regime_steps = 0
        
        # Regime returns (daily-ish)
        params = {
            "bull":  (0.0008, 0.012),   # +drift, low vol
            "bear":  (-0.0010, 0.020),  # -drift, mid vol
            "crash": (-0.015, 0.045),   # big -, high vol
        }
        mu, sigma = params[self.regime]
        equity_return = self.rng.normal(mu, sigma)
        return equity_return, sigma


# ============================================================
# Portfolio runner with Loom
# ============================================================

def run_loom_portfolio(loom_engine, horizon: int = 250,
                         seed: int = 42, rebalance_cost: float = 0.001) -> dict:
    """Loom v3.1 で portfolio allocation を運用."""
    adapter = PortfolioAdapter()
    market = SyntheticMarket(seed=seed)
    ps = PortfolioState()
    
    value_history = [ps.value]
    equity_history = [ps.equity_ratio]
    vol_buffer = []
    return_buffer = []
    
    for step in range(horizon):
        ps.step = step
        
        # 1. PortfolioState → Loom WorldState
        loom_state = adapter.portfolio_to_loom(ps)
        
        # 2. Loom decide
        decision = loom_engine.decide(loom_state)
        
        # 3. Loom action → target allocation
        target_equity = adapter.loom_action_to_allocation(decision.action, ps)
        
        # 4. Rebalance (cost を引く)
        rebalance_amount = abs(target_equity - ps.equity_ratio)
        ps.value *= (1 - rebalance_amount * rebalance_cost)
        ps.equity_ratio = target_equity
        ps.cash_ratio = 1 - target_equity
        
        # 5. Market step
        equity_return, vol = market.step()
        portfolio_return = ps.equity_ratio * equity_return  # cash = 0 return
        ps.value *= (1 + portfolio_return)
        ps.peak_value = max(ps.peak_value, ps.value)
        
        # 6. Update state estimates
        return_buffer.append(portfolio_return)
        vol_buffer.append(vol)
        if len(return_buffer) > 10:
            return_buffer.pop(0); vol_buffer.pop(0)
        ps.realized_vol = float(np.std(return_buffer)) if len(return_buffer) > 1 else 0.15
        ps.trend_strength = float(np.clip(np.mean(return_buffer) * 50, -1, 1)) if return_buffer else 0
        
        # 7. Reward (Loom feedback): risk-adjusted return
        reward = portfolio_return * 10 - ps.drawdown * 2
        sb = {"R": loom_state.R, "E": loom_state.E, "G": loom_state.G,
              "O": loom_state.O, "K": loom_state.K, "X": loom_state.X}
        ns = adapter.portfolio_to_loom(ps)
        sa = {"R": ns.R, "E": ns.E, "G": ns.G, "O": ns.O, "K": ns.K, "X": ns.X}
        loom_engine.update_reward(decision.action, reward, sb, sa)
        
        value_history.append(ps.value)
        equity_history.append(ps.equity_ratio)
        
        # 8. Ruin check
        if ps.drawdown >= adapter.RUIN_DRAWDOWN:
            ps.ruined = True
            break
    
    returns = np.diff(value_history) / np.array(value_history[:-1])
    sharpe = float(np.mean(returns) / (np.std(returns) + 1e-9) * np.sqrt(252)) if len(returns) > 1 else 0
    max_dd = max((max(value_history[:i+1]) - v) / max(value_history[:i+1])
                  for i, v in enumerate(value_history))
    
    return {
        "final_value": float(ps.value),
        "total_return": float(ps.value / 100.0 - 1),
        "max_drawdown": float(max_dd),
        "sharpe": sharpe,
        "ruined": ps.ruined,
        "survived_steps": ps.step + 1,
        "avg_equity": float(np.mean(equity_history)),
        "mode_counts": dict(loom_engine.stats["mode_counts"]),
    }


def run_buyhold_portfolio(horizon: int = 250, seed: int = 42,
                            equity_ratio: float = 0.6) -> dict:
    """Buy & Hold baseline (固定 allocation)."""
    market = SyntheticMarket(seed=seed)
    value = 100.0; peak = 100.0
    value_history = [value]
    ruined = False
    for step in range(horizon):
        equity_return, _ = market.step()
        value *= (1 + equity_ratio * equity_return)
        peak = max(peak, value)
        value_history.append(value)
        if (peak - value) / peak >= 0.40:
            ruined = True; break
    returns = np.diff(value_history) / np.array(value_history[:-1])
    sharpe = float(np.mean(returns) / (np.std(returns) + 1e-9) * np.sqrt(252)) if len(returns) > 1 else 0
    max_dd = max((max(value_history[:i+1]) - v) / max(value_history[:i+1])
                  for i, v in enumerate(value_history))
    return {
        "final_value": float(value), "total_return": float(value/100-1),
        "max_drawdown": float(max_dd), "sharpe": sharpe,
        "ruined": ruined, "survived_steps": len(value_history)-1,
    }


if __name__ == "__main__":
    print("=" * 72)
    print("NRMO/Loom を金融ポートフォリオに適用 — シミュレーション以外への汎用性")
    print("=" * 72)
    
    SEEDS = [42, 123, 777, 2024, 9999, 31337, 8080, 55555]
    HORIZON = 250
    
    loom_results = []
    bh_results = []
    
    for seed in SEEDS:
        loom = LoomV31(rng_manager=RNGManager(master_seed=seed + 700000),
                          use_qs_essence=True)
        lr = run_loom_portfolio(loom, horizon=HORIZON, seed=seed)
        bh = run_buyhold_portfolio(horizon=HORIZON, seed=seed, equity_ratio=0.6)
        loom_results.append(lr)
        bh_results.append(bh)
    
    def agg(rs):
        return {
            "return": float(np.mean([r["total_return"] for r in rs])),
            "max_dd": float(np.mean([r["max_drawdown"] for r in rs])),
            "sharpe": float(np.mean([r["sharpe"] for r in rs])),
            "ruin_rate": float(np.mean([r["ruined"] for r in rs])),
        }
    
    lm, bh = agg(loom_results), agg(bh_results)
    
    print(f"\n  全 {len(SEEDS)} seeds × {HORIZON} steps (synthetic regime-switching market)")
    print(f"\n  {'Metric':<18}{'Loom NRMO':>14}{'Buy&Hold 60%':>16}")
    print(f"  {'-'*18}{'-'*14}{'-'*16}")
    print(f"  {'total_return':<18}{lm['return']:>13.1%}{bh['return']:>15.1%}")
    print(f"  {'max_drawdown':<18}{lm['max_dd']:>13.1%}{bh['max_dd']:>15.1%}")
    print(f"  {'sharpe':<18}{lm['sharpe']:>14.2f}{bh['sharpe']:>16.2f}")
    print(f"  {'ruin_rate (DD>40%)':<18}{lm['ruin_rate']:>13.0%}{bh['ruin_rate']:>15.0%}")
    
    print(f"\n  Loom mode usage (last run): {loom_results[-1]['mode_counts']}")
    print(f"  Loom avg equity ratio: {loom_results[-1]['avg_equity']:.2f}")
    
    print("\n[NRMO/Loom が portfolio decision に適用可能 ✅]")
    print("→ civ-sim と同じ adapter pattern で、別 domain に転用できた")
