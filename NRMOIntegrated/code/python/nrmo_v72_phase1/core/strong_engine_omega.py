"""
core/strong_engine_omega.py

StrongEngine Ω Full v5.0 — 本来の正典.

これまで V8Engine 内で self.strong_engine = V71Engine (lite 紛い物) を使っていた.
v8.3 で StrongEngine Ω Full を本格実装し置換する.

機能:
  - mutation pathway:   action 微小変異
  - synthesis pathway:  既存 action 合成
  - invention pathway:  新規 action pathway 発見
  - Wolf Pursuit mode:  O 高い時の追跡攻撃
  - Edge Survival Guard: X 高い時の徹底防衛
  - λ_drift = 1.0:      戦略ドリフトへの抑制
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from collections import deque, Counter
import numpy as np
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

from world_models import Action, WorldState


# ============================================================
# Candidate Composite (mutation / synthesis / invention の結果)
# ============================================================

@dataclass
class CandidateAction:
    """通常 Action を内包し、生成方法と評価を保持"""
    action: Action
    source: str  # "base" / "mutation" / "synthesis" / "invention" / "wolf_pursuit" / "edge_guard"
    expected_value: float = 0.0
    expected_worst: float = 0.0
    expected_best: float = 0.0
    novelty: float = 0.0  # invention 度合い
    drift_distance: float = 0.0  # λ_drift 用


# ============================================================
# StrongEngineOmega
# ============================================================

class StrongEngineOmega:
    """StrongEngine Ω Full v5.0
    
    NRMO の許容範囲内で「攻める」候補を生成する.
    NRMO Core (CMDP, Falsifiability) で許容判定を受ける前提.
    """
    
    BASE_INTENTS = ["invest", "defend", "explore", "recover", "hold"]
    BASE_STRENGTHS = ["A", "B", "C"]
    
    # Wolf Pursuit / Edge Guard 発動閾値
    WOLF_PURSUIT_O_THRESHOLD = 65.0      # O がこの値以上で Wolf Pursuit 発動
    EDGE_GUARD_X_THRESHOLD = 65.0        # X がこの値以上で Edge Guard 発動
    
    # λ_drift
    LAMBDA_DRIFT = 1.0
    DRIFT_WINDOW = 10
    
    def __init__(self, rng: Optional[np.random.Generator] = None):
        self.rng = rng if rng is not None else np.random.default_rng()
        
        # 戦略履歴 (drift 計算用)
        self.strategy_history: deque = deque(maxlen=self.DRIFT_WINDOW)
        
        # Bandit-like 報酬履歴 (各 (intent, strength) ごと)
        self.reward_history: Dict[Tuple[str, str], List[float]] = {}
        self.action_count: Counter = Counter()
        
        # invention pathway 用の新規 action 候補プール
        # 既存 intent の組み合わせや変調された動作
        self.invented_actions: List[CandidateAction] = []
    
    # ============================================================
    # base 候補生成 (5 intents × 3 strengths = 15)
    # ============================================================
    
    def _generate_base_candidates(self, state: WorldState) -> List[CandidateAction]:
        candidates = []
        for intent in self.BASE_INTENTS:
            for strength in self.BASE_STRENGTHS:
                action = Action(intent=intent, strength=strength)
                ev, worst, best = self._estimate_action_values(state, action)
                candidates.append(CandidateAction(
                    action=action,
                    source="base",
                    expected_value=ev,
                    expected_worst=worst,
                    expected_best=best,
                ))
        return candidates
    
    # ============================================================
    # mutation pathway
    # ============================================================
    
    def _mutation_pathway(self, state: WorldState,
                            top_candidates: List[CandidateAction]
                            ) -> List[CandidateAction]:
        """上位候補の微小変異
        
        変異方法:
          - strength を 1 段階上下にずらす
          - intent を「隣接する」intent に置き換える
        """
        mutated = []
        
        # intent の隣接関係 (戦略空間上の近隣)
        adjacency = {
            "invest":  ["explore", "defend"],
            "defend":  ["recover", "hold", "invest"],
            "explore": ["invest", "hold"],
            "recover": ["defend", "hold"],
            "hold":    ["defend", "recover", "explore"],
        }
        
        for cand in top_candidates[:3]:  # 上位 3 候補から変異
            intent = cand.action.intent
            strength = cand.action.strength
            
            # Strength mutation
            strength_idx = self.BASE_STRENGTHS.index(strength)
            for delta in [-1, +1]:
                new_idx = strength_idx + delta
                if 0 <= new_idx < len(self.BASE_STRENGTHS):
                    new_action = Action(intent=intent, strength=self.BASE_STRENGTHS[new_idx])
                    ev, worst, best = self._estimate_action_values(state, new_action)
                    mutated.append(CandidateAction(
                        action=new_action,
                        source="mutation_strength",
                        expected_value=ev,
                        expected_worst=worst,
                        expected_best=best,
                    ))
            
            # Intent mutation (隣接へ)
            for adj_intent in adjacency.get(intent, []):
                new_action = Action(intent=adj_intent, strength=strength)
                ev, worst, best = self._estimate_action_values(state, new_action)
                mutated.append(CandidateAction(
                    action=new_action,
                    source="mutation_intent",
                    expected_value=ev,
                    expected_worst=worst,
                    expected_best=best,
                ))
        
        return mutated
    
    # ============================================================
    # synthesis pathway (合成 — 概念実装)
    # ============================================================
    
    def _synthesis_pathway(self, state: WorldState,
                             top_candidates: List[CandidateAction]
                             ) -> List[CandidateAction]:
        """既存 action の合成
        
        action 空間が離散なので、「組み合わせ」を以下で表現:
          - 2 candidates の中間値 (ev/worst/best の平均)
          - 評価のみ合成、final action は 2 つのうち良い方
        """
        synthesized = []
        
        if len(top_candidates) < 2:
            return synthesized
        
        # 上位 3 candidates から 2 つずつ組み合わせ
        for i in range(min(3, len(top_candidates))):
            for j in range(i + 1, min(3, len(top_candidates))):
                c1 = top_candidates[i]
                c2 = top_candidates[j]
                # 合成 = 期待値の重み付き平均、final action は state に応じて
                ev_synth = (c1.expected_value + c2.expected_value) / 2
                worst_synth = min(c1.expected_worst, c2.expected_worst)
                best_synth = max(c1.expected_best, c2.expected_best)
                
                # 「合成 action」として state に最適な方を選ぶ
                # 高 X → conservative (worst が大きい方)
                if state.X > 60:
                    chosen = c1 if c1.expected_worst > c2.expected_worst else c2
                else:
                    chosen = c1 if c1.expected_value > c2.expected_value else c2
                
                synth = CandidateAction(
                    action=chosen.action,
                    source=f"synthesis({c1.action.intent}/{c1.action.strength}+{c2.action.intent}/{c2.action.strength})",
                    expected_value=ev_synth,
                    expected_worst=worst_synth,
                    expected_best=best_synth,
                )
                synthesized.append(synth)
        
        return synthesized
    
    # ============================================================
    # invention pathway (新規発見)
    # ============================================================
    
    def _invention_pathway(self, state: WorldState) -> List[CandidateAction]:
        """既知 action vocabulary を超えた新規発見
        
        実装方針:
          - 過去履歴で「ほぼ試していない」(intent, strength) 組み合わせを上位に
          - 大量の連続失敗が起きていれば、稀有な action を提案
          - rng で確率的に novel action を generate
        """
        invented = []
        
        # 各 (intent, strength) の試行回数
        all_pairs = [(i, s) for i in self.BASE_INTENTS for s in self.BASE_STRENGTHS]
        try_counts = [self.action_count.get(pair, 0) for pair in all_pairs]
        min_count = min(try_counts) if try_counts else 0
        
        # 試行数が少ない action を novel として推薦
        novel_pairs = [pair for pair, c in zip(all_pairs, try_counts) 
                        if c <= min_count + 1]
        
        # ランダムに 2 つ選択
        if novel_pairs:
            chosen = self.rng.choice(len(novel_pairs), 
                                       size=min(2, len(novel_pairs)), 
                                       replace=False)
            for idx in chosen:
                intent, strength = novel_pairs[int(idx)]
                action = Action(intent=intent, strength=strength)
                ev, worst, best = self._estimate_action_values(state, action)
                # novelty 高い (試行数低い)
                novelty = 1.0 / (1.0 + self.action_count.get((intent, strength), 0))
                invented.append(CandidateAction(
                    action=action,
                    source="invention",
                    expected_value=ev,
                    expected_worst=worst,
                    expected_best=best,
                    novelty=novelty,
                ))
        
        return invented
    
    # ============================================================
    # Wolf Pursuit mode
    # ============================================================
    
    def _wolf_pursuit(self, state: WorldState) -> List[CandidateAction]:
        """機会窓 (O 高い) で集中攻撃を提案"""
        if state.O < self.WOLF_PURSUIT_O_THRESHOLD:
            return []
        
        # 攻撃的 action を強く推す
        wolf_candidates = []
        for strength in ["B", "C"]:
            for intent in ["invest", "explore"]:
                action = Action(intent=intent, strength=strength)
                ev, worst, best = self._estimate_action_values(state, action)
                # Wolf Pursuit bonus
                ev_boost = ev + 1.5 * (state.O - self.WOLF_PURSUIT_O_THRESHOLD) / 30
                wolf_candidates.append(CandidateAction(
                    action=action,
                    source="wolf_pursuit",
                    expected_value=ev_boost,
                    expected_worst=worst,
                    expected_best=best,
                ))
        
        return wolf_candidates
    
    # ============================================================
    # Edge Survival Guard
    # ============================================================
    
    def _edge_survival_guard(self, state: WorldState) -> List[CandidateAction]:
        """縁際 (X 高い) で生存特化"""
        if state.X < self.EDGE_GUARD_X_THRESHOLD:
            return []
        
        guard_candidates = []
        for strength in ["A", "B"]:
            for intent in ["defend", "recover"]:
                action = Action(intent=intent, strength=strength)
                ev, worst, best = self._estimate_action_values(state, action)
                # Edge Guard では worst が悪化しないことを評価
                worst_boost = worst + 2.0 * (state.X - self.EDGE_GUARD_X_THRESHOLD) / 30
                guard_candidates.append(CandidateAction(
                    action=action,
                    source="edge_guard",
                    expected_value=ev,
                    expected_worst=worst_boost,
                    expected_best=best,
                ))
        
        return guard_candidates
    
    # ============================================================
    # λ_drift penalty
    # ============================================================
    
    def _apply_drift_penalty(self, candidates: List[CandidateAction]
                                ) -> List[CandidateAction]:
        """戦略ドリフトを抑制
        
        最近の戦略履歴と比較し、大きく異なる action にペナルティ.
        """
        if len(self.strategy_history) < 3:
            return candidates  # 履歴不足
        
        # 最近の (intent, strength) 頻度
        recent = list(self.strategy_history)
        recent_counter = Counter(recent)
        
        for cand in candidates:
            key = (cand.action.intent, cand.action.strength)
            frequency = recent_counter.get(key, 0) / len(recent)
            # 頻度が低いほど drift_distance 大
            cand.drift_distance = 1.0 - frequency
            # λ_drift で penalty
            penalty = self.LAMBDA_DRIFT * cand.drift_distance * 0.3
            cand.expected_value -= penalty
        
        return candidates
    
    # ============================================================
    # Action value estimation
    # ============================================================
    
    def _estimate_action_values(self, state: WorldState, action: Action
                                  ) -> Tuple[float, float, float]:
        """期待値、最悪、最良"""
        # 過去 reward 履歴から学習 (Bandit-ish)
        key = (action.intent, action.strength)
        history = self.reward_history.get(key, [])
        
        if history:
            ev = float(np.mean(history))
            worst = float(np.percentile(history, 25))
            best = float(np.percentile(history, 75))
        else:
            # 履歴なし → state ベース推定
            base = (state.R + state.E + state.G) / 300 * 0.5
            
            intent_factor = {
                "invest": 1.5, "explore": 1.0, "defend": 0.5,
                "recover": 0.8, "hold": 0.2,
            }.get(action.intent, 0.5)
            
            strength_mult = {"A": 1.0, "B": 1.5, "C": 2.0}.get(action.strength, 1.0)
            
            ev = base + intent_factor * strength_mult * 0.3
            
            # 不確実性 (state X 高いほど worst が悪化)
            uncertainty = state.X / 100 * 2.0
            worst = ev - uncertainty
            best = ev + uncertainty * 0.5
        
        return float(ev), float(worst), float(best)
    
    # ============================================================
    # Main generate
    # ============================================================
    
    def generate_candidates(self, state: WorldState) -> List[CandidateAction]:
        """全 pathway を回して候補生成
        
        Returns: CandidateAction のリスト (重複あり、ranked されている)
        """
        # Base
        base = self._generate_base_candidates(state)
        
        # Sort base by expected_value
        base_sorted = sorted(base, key=lambda c: -c.expected_value)
        top_base = base_sorted[:5]
        
        # Mutation
        mutations = self._mutation_pathway(state, top_base)
        
        # Synthesis
        syntheses = self._synthesis_pathway(state, top_base)
        
        # Invention
        inventions = self._invention_pathway(state)
        
        # Wolf Pursuit (条件発動)
        wolf = self._wolf_pursuit(state)
        
        # Edge Survival Guard (条件発動)
        edge = self._edge_survival_guard(state)
        
        # All candidates
        all_candidates = base + mutations + syntheses + inventions + wolf + edge
        
        # λ_drift penalty
        all_candidates = self._apply_drift_penalty(all_candidates)
        
        # Sort by expected_value (with drift penalty applied)
        all_candidates.sort(key=lambda c: -c.expected_value)
        
        return all_candidates
    
    def select_action(self, state: WorldState) -> Action:
        """単一 action を選ぶ (legacy V71Engine 互換)"""
        candidates = self.generate_candidates(state)
        if candidates:
            return candidates[0].action
        return Action(intent="hold", strength="A")
    
    def update_reward(self, action: Action, reward: float):
        """報酬 update (Bandit)"""
        key = (action.intent, action.strength)
        if key not in self.reward_history:
            self.reward_history[key] = []
        self.reward_history[key].append(float(reward))
        # 履歴は最大 50 件
        if len(self.reward_history[key]) > 50:
            self.reward_history[key] = self.reward_history[key][-50:]
        
        self.action_count[key] += 1
        self.strategy_history.append(key)


# ============================================================
# Test
# ============================================================

if __name__ == "__main__":
    from world_models import World, WorldType
    
    print("=" * 70)
    print("StrongEngine Ω Full Test")
    print("=" * 70)
    
    rng = np.random.default_rng(42)
    engine = StrongEngineOmega(rng=rng)
    
    world = World(WorldType.NORMAL, seed=42)
    
    for t in range(5):
        candidates = engine.generate_candidates(world.state)
        action = candidates[0].action
        
        print(f"\nt={t+1}: state O={world.state.O:.1f}, X={world.state.X:.1f}")
        print(f"  Top 5 candidates:")
        for i, c in enumerate(candidates[:5]):
            print(f"    {i+1}. {c.action.intent}/{c.action.strength} "
                  f"(ev={c.expected_value:.3f}, source={c.source})")
        
        _, reward, done, _ = world.step(action)
        engine.update_reward(action, reward)
        if done:
            break
    
    # Wolf Pursuit / Edge Guard が発動する状態でも試す
    print("\n\n=== Wolf Pursuit test (O=80) ===")
    world.state.O = 80.0
    candidates = engine.generate_candidates(world.state)
    wolf_cands = [c for c in candidates if c.source == "wolf_pursuit"]
    print(f"Wolf Pursuit candidates: {len(wolf_cands)}")
    for c in wolf_cands[:3]:
        print(f"  {c.action.intent}/{c.action.strength} (ev={c.expected_value:.3f})")
    
    print("\n=== Edge Survival Guard test (X=80) ===")
    world.state.X = 80.0
    world.state.O = 40.0  # Wolf を切る
    candidates = engine.generate_candidates(world.state)
    guard_cands = [c for c in candidates if c.source == "edge_guard"]
    print(f"Edge Guard candidates: {len(guard_cands)}")
    for c in guard_cands[:3]:
        print(f"  {c.action.intent}/{c.action.strength} (ev={c.expected_value:.3f})")
    
    print("\n[StrongEngine Ω Full 動作確認 完了 ✅]")
