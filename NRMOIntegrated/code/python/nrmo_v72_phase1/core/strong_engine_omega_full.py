"""
core/strong_engine_omega_full.py

StrongEngineΩfull — handoff doc § 14 の正典構造.

Internal structure:
  StrongEngineΩfull
    ├─ DefensiveCandidateModule
    ├─ RecoveryCandidateModule
    ├─ ExplorationCandidateModule
    ├─ MutationPathway
    ├─ SynthesisPathway
    ├─ InventionPathway
    ├─ AggressiveEngine Submodule (handoff doc § 6-13)
    │    ├─ Wolf Pursuit Mode
    │    ├─ Small Reversible Attack Mode
    │    ├─ Anti-Stagnation Attack Mode
    │    └─ Momentum Exploitation Mode
    └─ CandidateMerger

AggressiveEngine は独立 engine ではなく、StrongEngineΩfull 内部の補助.
candidate を生成するのみ、最終決定権は持たない.

Each AggressiveEngine candidate output schema (handoff doc § 11):
  {
    "module": "AggressiveEngine",
    "mode": "...",
    "attack_candidate": "intent/strength",
    "safe_variant": "intent/strength",
    "minimum_reversible_variant": "intent/strength",
    "expected_upside": float,
    "estimated_downside": float,
    "reversibility": float,
    "required_conditions": dict,
    "stop_conditions": dict,
    "reason": str,
  }
"""
from __future__ import annotations
import os
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from collections import deque
import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

from world_models import WorldState, Action
from map_layer import MAPLayer


# ============================================================
# Candidate schema
# ============================================================

@dataclass
class FullCandidate:
    """All modules' output candidate"""
    module: str                  # "DefensiveCandidate", "RecoveryCandidate", ..., "AggressiveEngine"
    mode: Optional[str] = None   # AggressiveEngine 内部 mode
    
    attack_candidate: Optional[Action] = None        # 主候補
    safe_variant: Optional[Action] = None            # 縮小版
    minimum_reversible_variant: Optional[Action] = None  # 最小可逆版
    
    expected_upside: float = 0.0
    estimated_downside: float = 0.0
    reversibility: float = 0.5
    
    required_conditions: Dict = field(default_factory=dict)
    stop_conditions: Dict = field(default_factory=dict)
    
    reason: str = ""
    
    def to_dict(self) -> Dict:
        def a2s(a):
            return f"{a.intent}/{a.strength}" if a else None
        return {
            "module": self.module,
            "mode": self.mode,
            "attack_candidate": a2s(self.attack_candidate),
            "safe_variant": a2s(self.safe_variant),
            "minimum_reversible_variant": a2s(self.minimum_reversible_variant),
            "expected_upside": self.expected_upside,
            "estimated_downside": self.estimated_downside,
            "reversibility": self.reversibility,
            "required_conditions": self.required_conditions,
            "stop_conditions": self.stop_conditions,
            "reason": self.reason,
        }


# ============================================================
# DefensiveCandidateModule
# ============================================================

class DefensiveCandidateModule:
    """守りの候補生成"""
    
    def generate(self, state: WorldState,
                   map_layer: Optional[MAPLayer] = None) -> List[FullCandidate]:
        cands = []
        
        # defend/A (基本)
        c = FullCandidate(
            module="DefensiveCandidate",
            attack_candidate=Action("defend", "A"),
            safe_variant=Action("defend", "A"),
            minimum_reversible_variant=Action("hold", "A"),
            expected_upside=0.3,
            estimated_downside=0.05,
            reversibility=0.95,
            reason="basic defensive posture",
        )
        cands.append(c)
        
        # X が高い → defend/B も提案
        if state.X > 50:
            c = FullCandidate(
                module="DefensiveCandidate",
                attack_candidate=Action("defend", "B"),
                safe_variant=Action("defend", "A"),
                minimum_reversible_variant=Action("hold", "A"),
                expected_upside=0.4,
                estimated_downside=0.15,
                reversibility=0.85,
                reason=f"X={state.X:.0f} high, stronger defend",
            )
            cands.append(c)
        
        return cands


# ============================================================
# RecoveryCandidateModule
# ============================================================

class RecoveryCandidateModule:
    """回復の候補"""
    
    def generate(self, state: WorldState,
                   map_layer: Optional[MAPLayer] = None) -> List[FullCandidate]:
        cands = []
        
        # recover/A
        c = FullCandidate(
            module="RecoveryCandidate",
            attack_candidate=Action("recover", "A"),
            safe_variant=Action("recover", "A"),
            minimum_reversible_variant=Action("hold", "A"),
            expected_upside=0.5,
            estimated_downside=0.05,
            reversibility=0.95,
            reason="resource recovery",
        )
        cands.append(c)
        
        # E or R が低ければ recover/B
        if state.E < 40 or state.R < 35:
            c = FullCandidate(
                module="RecoveryCandidate",
                attack_candidate=Action("recover", "B"),
                safe_variant=Action("recover", "A"),
                minimum_reversible_variant=Action("hold", "A"),
                expected_upside=0.7,
                estimated_downside=0.15,
                reversibility=0.80,
                reason="E or R low, stronger recovery",
            )
            cands.append(c)
        
        return cands


# ============================================================
# ExplorationCandidateModule
# ============================================================

class ExplorationCandidateModule:
    """探索の候補"""
    
    def generate(self, state: WorldState,
                   map_layer: Optional[MAPLayer] = None) -> List[FullCandidate]:
        cands = []
        
        c = FullCandidate(
            module="ExplorationCandidate",
            attack_candidate=Action("explore", "A"),
            safe_variant=Action("explore", "A"),
            minimum_reversible_variant=Action("hold", "A"),
            expected_upside=0.4,
            estimated_downside=0.1,
            reversibility=0.90,
            reason="information gathering",
        )
        cands.append(c)
        
        # K (knowledge) が低い + 余裕あれば B も
        if state.K < 50 and state.R >= 40:
            c = FullCandidate(
                module="ExplorationCandidate",
                attack_candidate=Action("explore", "B"),
                safe_variant=Action("explore", "A"),
                minimum_reversible_variant=Action("hold", "A"),
                expected_upside=0.6,
                estimated_downside=0.2,
                reversibility=0.80,
                reason="K low and R sufficient, broader exploration",
            )
            cands.append(c)
        
        return cands


# ============================================================
# MutationPathway
# ============================================================

class MutationPathway:
    """既存候補の微小変異"""
    
    def generate(self, state: WorldState,
                   base_candidates: List[FullCandidate],
                   map_layer: Optional[MAPLayer] = None) -> List[FullCandidate]:
        """base 候補から派生"""
        if not base_candidates:
            return []
        
        mutated = []
        for base in base_candidates[:3]:
            if not base.attack_candidate:
                continue
            # strength を 1 段階上下
            intent = base.attack_candidate.intent
            cur_strength = base.attack_candidate.strength
            
            strengths = ["A", "B", "C"]
            idx = strengths.index(cur_strength)
            for new_idx in [idx - 1, idx + 1]:
                if 0 <= new_idx < 3:
                    new_strength = strengths[new_idx]
                    new_action = Action(intent, new_strength)
                    
                    c = FullCandidate(
                        module="MutationPathway",
                        attack_candidate=new_action,
                        safe_variant=Action(intent, "A"),
                        minimum_reversible_variant=Action("hold", "A"),
                        expected_upside=base.expected_upside * 0.9,
                        estimated_downside=base.estimated_downside * 1.1,
                        reversibility=base.reversibility * 0.95,
                        reason=f"mutation of {base.module} ({cur_strength}->{new_strength})",
                    )
                    mutated.append(c)
        
        return mutated


# ============================================================
# SynthesisPathway
# ============================================================

class SynthesisPathway:
    """既存候補の合成"""
    
    def generate(self, state: WorldState,
                   base_candidates: List[FullCandidate],
                   map_layer: Optional[MAPLayer] = None) -> List[FullCandidate]:
        if len(base_candidates) < 2:
            return []
        
        synthesized = []
        # 上位 3 個から 2 個ずつ合成 (期待値の平均、stop_conditions の union)
        for i in range(min(3, len(base_candidates))):
            for j in range(i + 1, min(3, len(base_candidates))):
                a = base_candidates[i]
                b = base_candidates[j]
                if not a.attack_candidate or not b.attack_candidate:
                    continue
                
                # state に応じて選ぶ (高 X → 保守側、低 X → 攻撃側)
                if state.X > 60:
                    chosen = a if a.estimated_downside < b.estimated_downside else b
                else:
                    chosen = a if a.expected_upside > b.expected_upside else b
                
                c = FullCandidate(
                    module="SynthesisPathway",
                    attack_candidate=chosen.attack_candidate,
                    safe_variant=chosen.safe_variant,
                    minimum_reversible_variant=chosen.minimum_reversible_variant,
                    expected_upside=(a.expected_upside + b.expected_upside) / 2,
                    estimated_downside=max(a.estimated_downside, b.estimated_downside),
                    reversibility=min(a.reversibility, b.reversibility),
                    reason=f"synthesis({a.module}+{b.module})",
                )
                synthesized.append(c)
        
        return synthesized


# ============================================================
# InventionPathway
# ============================================================

class InventionPathway:
    """新規 action の発見"""
    
    def __init__(self, rng: Optional[np.random.Generator] = None):
        self.rng = rng if rng is not None else np.random.default_rng()
        self.tried_actions: Dict[Tuple[str, str], int] = {}
    
    def generate(self, state: WorldState,
                   map_layer: Optional[MAPLayer] = None) -> List[FullCandidate]:
        """tried_actions count が少ない (intent, strength) を invention として推奨"""
        all_pairs = [(i, s) for i in ["invest", "defend", "explore", "recover", "hold"]
                      for s in ["A", "B", "C"]]
        
        counts = [(p, self.tried_actions.get(p, 0)) for p in all_pairs]
        counts.sort(key=lambda x: x[1])
        
        invented = []
        # 最も試行数が少ない 2 つ
        for pair, n_tried in counts[:2]:
            if n_tried < 3:  # 試行が少ないものを invention とする
                action = Action(pair[0], pair[1])
                c = FullCandidate(
                    module="InventionPathway",
                    attack_candidate=action,
                    safe_variant=Action(pair[0], "A"),
                    minimum_reversible_variant=Action("hold", "A"),
                    expected_upside=0.5,  # 不確実だが novel
                    estimated_downside=0.3,
                    reversibility=0.7,
                    reason=f"invention: novel action {action.intent}/{action.strength} (tried {n_tried} times)",
                )
                invented.append(c)
        
        return invented
    
    def record_action(self, action: Action):
        key = (action.intent, action.strength)
        self.tried_actions[key] = self.tried_actions.get(key, 0) + 1


# ============================================================
# AggressiveEngine Submodule (handoff doc § 8-13)
# ============================================================

class AggressiveEngineSubmodule:
    """StrongEngineΩfull 内部の AggressiveEngine.
    
    NOT independent. Auxiliary candidate generator.
    No final-action authority.
    
    Output: Bounded, reversible, condition-aware offensive candidates.
    """
    
    # Activation conditions (handoff doc § 12)
    ACT_R_MIN = 40
    ACT_E_MIN_NORM = 0.45
    ACT_X_MAX_NORM = 0.60
    ACT_O_CONFIDENCE_MIN = 0.65
    
    # Suppression conditions
    SUPP_R_CRITICAL = 15
    SUPP_R_C_PROHIBITED = 25
    SUPP_X_C_PROHIBITED_NORM = 0.75
    SUPP_X_TRUE_VETO_NORM = 0.90
    
    def __init__(self):
        self.modes = ["wolf_pursuit", "small_reversible_attack",
                       "anti_stagnation", "momentum_exploitation"]
        
        # ★ Detailed lifecycle counters (handoff doc § 12)
        self.counters = {
            "generated_count": 0,        # 候補が生成された
            "eligible_count": 0,         # activation 通過 (mode 別 generate に到達)
            "guard_passed_count": 0,     # 後続 pipeline で guard 通過 (set by external)
            "selected_by_merger_count": 0,  # merger で選ばれた (set by external)
            "final_accepted_count": 0,   # 最終採用 (set by external)
            "blocked_by_guard_count": 0,
            "blocked_by_merger_count": 0,
            "blocked_by_revalidation_count": 0,
            "blocked_reason_histogram": {},  # reason -> count
        }
        # Mode-level counters
        self.mode_counters = {m: {"generated": 0, "selected": 0} for m in self.modes}
    
    # ============================================================
    # Activation / Suppression gates
    # ============================================================
    
    def _is_activated(self, state: WorldState, 
                       conditions: Optional[Dict] = None) -> Tuple[bool, str]:
        """Activation conditions check (handoff doc § 12)"""
        if state.R < self.ACT_R_MIN:
            return False, f"R={state.R:.0f} < {self.ACT_R_MIN}"
        if state.E / 100 < self.ACT_E_MIN_NORM:
            return False, f"E={state.E:.0f} < {self.ACT_E_MIN_NORM*100:.0f}"
        if state.X / 100 > self.ACT_X_MAX_NORM:
            return False, f"X={state.X:.0f} > {self.ACT_X_MAX_NORM*100:.0f}"
        
        if conditions is None:
            return True, "all activation conditions met"
        
        # O confidence
        if conditions.get("O_confidence", 1.0) < self.ACT_O_CONFIDENCE_MIN:
            return False, "O confidence too low"
        if conditions.get("recent_drawdown", False):
            return False, "recent drawdown active"
        if conditions.get("true_veto", False):
            return False, "true_veto active"
        
        return True, "all activation conditions met"
    
    def _is_suppressed(self, state: WorldState, 
                         conditions: Optional[Dict] = None) -> Tuple[bool, str, str]:
        """Suppression check. Returns: (suppressed, reason, max_strength_allowed)"""
        # R critical
        if state.R <= self.SUPP_R_CRITICAL:
            return True, f"R={state.R:.0f} <= {self.SUPP_R_CRITICAL}", "none"  # no aggressive
        
        # R = recover/A priority
        if state.R <= 10:
            return True, "R<=10, AggressiveEngine inactive", "none"
        
        # X true veto
        if state.X / 100 >= self.SUPP_X_TRUE_VETO_NORM:
            return True, "X true veto", "none"
        
        # Determine max strength
        max_strength = "C"
        if state.R <= self.SUPP_R_C_PROHIBITED:
            max_strength = "B"
        if state.X / 100 >= self.SUPP_X_C_PROHIBITED_NORM:
            max_strength = "B"
        
        return False, f"max strength {max_strength}", max_strength
    
    # ============================================================
    # Mode-specific generators
    # ============================================================
    
    def _wolf_pursuit(self, state: WorldState, max_strength: str,
                        conditions: Optional[Dict]) -> Optional[FullCandidate]:
        """機会窓を集中的に追跡"""
        if state.O < 60:
            return None  # 機会窓なし
        
        # 強度: O が高いほど大きく (max_strength 内で)
        if state.O >= 75 and max_strength == "C":
            attack_strength = "B"  # safe-er than C
        elif state.O >= 65:
            attack_strength = "A" if max_strength == "A" else "B"
        else:
            attack_strength = "A"
        
        return FullCandidate(
            module="AggressiveEngine",
            mode="wolf_pursuit",
            attack_candidate=Action("invest", attack_strength),
            safe_variant=Action("invest", "A"),
            minimum_reversible_variant=Action("explore", "A"),
            expected_upside=0.7,
            estimated_downside=0.25,
            reversibility=0.75 if attack_strength == "A" else 0.55,
            required_conditions={
                "O_min": 60,
                "R_min": self.ACT_R_MIN,
                "X_max": self.SUPP_X_C_PROHIBITED_NORM * 100,
            },
            stop_conditions={
                "O_decay_below": 50,
                "R_drop_below": 30,
                "X_rise_above": 75,
                "two_failed_attempts": True,
            },
            reason=f"Wolf Pursuit: O={state.O:.0f}, attack_strength={attack_strength}",
        )
    
    def _small_reversible_attack(self, state: WorldState, max_strength: str,
                                    conditions: Optional[Dict]) -> Optional[FullCandidate]:
        """小さく可逆な攻撃"""
        # 常に A 強度 (small reversible)
        # invest/A or explore/A を context で選択
        if state.O > state.K:
            intent = "invest"
        else:
            intent = "explore"
        
        return FullCandidate(
            module="AggressiveEngine",
            mode="small_reversible_attack",
            attack_candidate=Action(intent, "A"),
            safe_variant=Action(intent, "A"),
            minimum_reversible_variant=Action("hold", "A"),
            expected_upside=0.45,
            estimated_downside=0.12,
            reversibility=0.92,
            required_conditions={
                "R_min": self.ACT_R_MIN,
            },
            stop_conditions={
                "R_drop_below": 30,
                "two_failed_attempts": True,
            },
            reason=f"Small reversible: {intent}/A",
        )
    
    def _anti_stagnation(self, state: WorldState, max_strength: str,
                           conditions: Optional[Dict]) -> Optional[FullCandidate]:
        """停滞打破: state 改善が低迷していたら attack"""
        # MAPLayer L2 trends 必要 (conditions に含まれる場合)
        if conditions is None:
            return None
        
        avg_score_trend = conditions.get("score_trend", None)
        if avg_score_trend is None or avg_score_trend >= 0:
            return None  # 停滞してない
        
        # 停滞: explore/B or invest/A で打破試行
        if max_strength == "C":
            attack_strength = "B"
        elif max_strength == "B":
            attack_strength = "B"
        else:
            attack_strength = "A"
        
        return FullCandidate(
            module="AggressiveEngine",
            mode="anti_stagnation",
            attack_candidate=Action("explore", attack_strength),
            safe_variant=Action("explore", "A"),
            minimum_reversible_variant=Action("hold", "A"),
            expected_upside=0.55,
            estimated_downside=0.20,
            reversibility=0.80,
            required_conditions={
                "stagnation_detected": True,
                "R_min": self.ACT_R_MIN,
            },
            stop_conditions={
                "R_drop_below": 30,
                "score_still_stagnant_after_3_steps": True,
            },
            reason=f"Anti-stagnation: explore/{attack_strength}",
        )
    
    def _momentum_exploitation(self, state: WorldState, max_strength: str,
                                  conditions: Optional[Dict]) -> Optional[FullCandidate]:
        """好調維持: 直近 reward が positive trend なら継続"""
        if conditions is None:
            return None
        
        recent_reward_trend = conditions.get("reward_trend", None)
        if recent_reward_trend is None or recent_reward_trend <= 0:
            return None
        
        # Momentum あり: 直近成功 action を継続
        recent_action = conditions.get("recent_successful_action", None)
        if recent_action is None:
            return None
        
        intent, strength = recent_action
        # max_strength を超えない
        if strength == "C" and max_strength != "C":
            strength = max_strength
        
        return FullCandidate(
            module="AggressiveEngine",
            mode="momentum_exploitation",
            attack_candidate=Action(intent, strength),
            safe_variant=Action(intent, "A"),
            minimum_reversible_variant=Action("hold", "A"),
            expected_upside=0.6,
            estimated_downside=0.18,
            reversibility=0.78 if strength == "A" else 0.65,
            required_conditions={
                "positive_reward_trend": True,
                "R_min": self.ACT_R_MIN,
            },
            stop_conditions={
                "reward_trend_reverses": True,
                "R_drop_below": 30,
            },
            reason=f"Momentum: continue {intent}/{strength}",
        )
    
    # ============================================================
    # Main generate
    # ============================================================
    
    def generate(self, state: WorldState,
                   conditions: Optional[Dict] = None,
                   map_layer: Optional[MAPLayer] = None,
                   forced_diagnostic: bool = False) -> List[FullCandidate]:
        """AggressiveEngine candidate 生成 (with detailed logging § 12)"""
        # 1. Activation check (skipped in forced_diagnostic)
        if not forced_diagnostic:
            activated, act_reason = self._is_activated(state, conditions)
            if not activated:
                # logging: blocked at activation
                reason = f"activation_failed: {act_reason}"
                self.counters["blocked_reason_histogram"][reason] = \
                    self.counters["blocked_reason_histogram"].get(reason, 0) + 1
                return []
        
        # 2. Suppression check (always applies, even in forced_diagnostic)
        suppressed, supp_reason, max_strength = self._is_suppressed(state, conditions)
        if suppressed:
            reason = f"suppressed: {supp_reason}"
            self.counters["blocked_reason_histogram"][reason] = \
                self.counters["blocked_reason_histogram"].get(reason, 0) + 1
            return []
        
        # 3. 各 mode の generator を呼ぶ
        cands = []
        
        for mode in self.modes:
            if mode == "wolf_pursuit":
                c = self._wolf_pursuit(state, max_strength, conditions)
            elif mode == "small_reversible_attack":
                c = self._small_reversible_attack(state, max_strength, conditions)
            elif mode == "anti_stagnation":
                c = self._anti_stagnation(state, max_strength, conditions)
            elif mode == "momentum_exploitation":
                c = self._momentum_exploitation(state, max_strength, conditions)
            else:
                c = None
            
            if c is not None:
                cands.append(c)
                self.mode_counters[mode]["generated"] += 1
        
        # ★ counters update
        self.counters["generated_count"] += len(cands)
        if cands:
            self.counters["eligible_count"] += 1  # この turn は eligible
        
        return cands
    
    def record_selection(self, candidate: FullCandidate):
        """External: merger でこの candidate が選ばれた時呼ぶ"""
        if candidate.module != "AggressiveEngine":
            return
        self.counters["selected_by_merger_count"] += 1
        if candidate.mode in self.mode_counters:
            self.mode_counters[candidate.mode]["selected"] += 1
    
    def record_block(self, candidate: FullCandidate, reason: str):
        """External: pipeline 後段で block された時呼ぶ"""
        if candidate.module != "AggressiveEngine":
            return
        if "guard" in reason.lower():
            self.counters["blocked_by_guard_count"] += 1
        elif "revalidation" in reason.lower():
            self.counters["blocked_by_revalidation_count"] += 1
        elif "merger" in reason.lower():
            self.counters["blocked_by_merger_count"] += 1
        
        self.counters["blocked_reason_histogram"][reason] = \
            self.counters["blocked_reason_histogram"].get(reason, 0) + 1
    
    def record_final_accept(self, candidate: FullCandidate):
        """External: 最終採用された時"""
        if candidate.module != "AggressiveEngine":
            return
        self.counters["final_accepted_count"] += 1


# ============================================================
# CandidateMerger
# ============================================================

class CandidateMerger:
    """各 module からの候補を統合し、最良候補をスコアリング"""
    
    def __init__(self, w_upside: float = 1.0, w_downside: float = 1.5,
                  w_reversibility: float = 0.5):
        self.w_upside = w_upside
        self.w_downside = w_downside  # downside heavier (NRMO spirit)
        self.w_reversibility = w_reversibility
    
    def score(self, cand: FullCandidate, state: WorldState) -> float:
        """NRMO 的スコア（状態適応）: upside - heavier(downside) + reversibility 加点。

        従来は state 未使用で downside/reversibility 重みが固定 → 余力が潤沢でも
        最安全候補(recover)が常勝し、過防御に陥っていた。NRMO の設計意図
        （最大前進 + 破滅縁ステアリング。停滞も死）に沿い、状態の安全余裕 margin が
        大きいほど upside を厚く・downside/reversibility を薄く評価する。脆弱時は従来の守り。
        """
        R = float(getattr(state, "R", 60)) / 100.0
        E = float(getattr(state, "E", 70)) / 100.0
        G = float(getattr(state, "G", 70)) / 100.0
        X = float(getattr(state, "X", 20)) / 100.0
        margin = max(0.0, min(1.0, 0.5 * min(E, G) + 0.3 * R + 0.2 * (1.0 - X)))
        w_up = self.w_upside * (1.0 + 1.2 * margin)          # 1.0 → 2.2
        w_dn = self.w_downside * (1.0 - 0.5 * margin)         # 1.5 → 0.75
        w_rev = self.w_reversibility * (1.0 - 0.5 * margin)   # 0.5 → 0.25
        base = (
            w_up * cand.expected_upside
            - w_dn * cand.estimated_downside
            + w_rev * cand.reversibility
        )
        # 停滞コスト（受動的死）: 余力が十分（margin>0.35）なのに守り続ける手は機会損失として減点。
        # NRMO 原理「停滞も死／最大前進」を符号化。脆弱時（margin<=0.35）は発生せず守りを尊重するため、
        # 勾配は 守り(recover) → 小さく試す(explore) → 投資(invest) と段階的に前進する。
        intent = getattr(getattr(cand, "attack_candidate", None), "intent", "") or ""
        defensive = intent in ("recover", "defend", "hold", "wait", "retreat", "stay")
        if defensive:
            base -= 1.0 * max(0.0, margin - 0.35)
        return base
    
    def merge(self, all_candidates: List[FullCandidate],
                state: WorldState) -> List[Tuple[FullCandidate, float]]:
        """Returns: List of (candidate, score), sorted by score descending"""
        scored = [(c, self.score(c, state)) for c in all_candidates]
        scored.sort(key=lambda x: -x[1])
        return scored


# ============================================================
# StrongEngineOmegaFull (統合)
# ============================================================

class StrongEngineOmegaFull:
    """StrongEngineΩfull: 全 module 統合
    
    Module ablation 用に各 module の enable/disable を制御可能.
    """
    
    def __init__(self, rng: Optional[np.random.Generator] = None,
                  enable_defensive: bool = True,
                  enable_recovery: bool = True,
                  enable_exploration: bool = True,
                  enable_mutation: bool = True,
                  enable_synthesis: bool = True,
                  enable_invention: bool = True,
                  enable_aggressive: bool = True):
        self.rng = rng if rng is not None else np.random.default_rng()
        
        # Module enable flags (for ablation studies)
        self.enable_defensive = enable_defensive
        self.enable_recovery = enable_recovery
        self.enable_exploration = enable_exploration
        self.enable_mutation = enable_mutation
        self.enable_synthesis = enable_synthesis
        self.enable_invention = enable_invention
        self.enable_aggressive = enable_aggressive
        
        # Module instances (always created, but conditionally used)
        self.defensive = DefensiveCandidateModule()
        self.recovery = RecoveryCandidateModule()
        self.exploration = ExplorationCandidateModule()
        self.mutation = MutationPathway()
        self.synthesis = SynthesisPathway()
        invention_rng = np.random.default_rng(int(self.rng.integers(0, 2**31)))
        self.invention = InventionPathway(rng=invention_rng)
        self.aggressive = AggressiveEngineSubmodule()
        self.merger = CandidateMerger()
        
        self.stats = {
            "n_defensive": 0, "n_recovery": 0, "n_exploration": 0,
            "n_mutation": 0, "n_synthesis": 0, "n_invention": 0,
            "n_aggressive": 0, "n_aggressive_modes": {},
        }
    
    def generate_all_candidates(self, state: WorldState,
                                  conditions: Optional[Dict] = None,
                                  map_layer: Optional[MAPLayer] = None,
                                  aggressive_forced_diagnostic: bool = False,
                                  # ★ sociable essence hooks (optional)
                                  failure_tracker=None,
                                  apply_canonical_dedup: bool = False,
                                  ) -> List[FullCandidate]:
        """全 module 候補生成 (ablation flags + diagnostic mode + sociable essence).
        
        Per sociable numbers エッセンス:
          - failure_tracker: 過去 fail した (thread, state-sig) を pre-reject
          - apply_canonical_dedup: 候補を canonical key で重複排除
        """
        all_cands = []
        
        # Base modules
        def_cands = self.defensive.generate(state, map_layer) if self.enable_defensive else []
        rec_cands = self.recovery.generate(state, map_layer) if self.enable_recovery else []
        exp_cands = self.exploration.generate(state, map_layer) if self.enable_exploration else []
        
        all_cands.extend(def_cands)
        all_cands.extend(rec_cands)
        all_cands.extend(exp_cands)
        
        # Pathways
        mut_cands = (self.mutation.generate(state, all_cands[:6], map_layer)
                       if self.enable_mutation else [])
        syn_cands = (self.synthesis.generate(state, all_cands[:6], map_layer)
                       if self.enable_synthesis else [])
        inv_cands = (self.invention.generate(state, map_layer)
                       if self.enable_invention else [])
        
        all_cands.extend(mut_cands)
        all_cands.extend(syn_cands)
        all_cands.extend(inv_cands)
        
        # ★ AggressiveEngine (with forced_diagnostic option)
        agg_cands = (self.aggressive.generate(state, conditions, map_layer,
                                                forced_diagnostic=aggressive_forced_diagnostic)
                       if self.enable_aggressive else [])
        all_cands.extend(agg_cands)
        
        # Stats
        self.stats["n_defensive"] += len(def_cands)
        self.stats["n_recovery"] += len(rec_cands)
        self.stats["n_exploration"] += len(exp_cands)
        self.stats["n_mutation"] += len(mut_cands)
        self.stats["n_synthesis"] += len(syn_cands)
        self.stats["n_invention"] += len(inv_cands)
        self.stats["n_aggressive"] += len(agg_cands)
        for c in agg_cands:
            mode = c.mode
            self.stats["n_aggressive_modes"][mode] = \
                self.stats["n_aggressive_modes"].get(mode, 0) + 1
        
        # === Sociable Essence Application (optional hooks) ===
        # Per sociable numbers: failure-face residue avoidance + canonical dedup
        if failure_tracker is not None:
            # Module name → Thread name mapping (light import to avoid circular)
            try:
                from loom_core import MODULE_TO_THREAD
                filtered = []
                pre_rejected_count = 0
                for c in all_cands:
                    thread = MODULE_TO_THREAD.get(c.module)
                    if thread is None:
                        filtered.append(c)
                        continue
                    should_reject, _ = failure_tracker.should_pre_reject(
                        thread.value, state
                    )
                    if should_reject:
                        pre_rejected_count += 1
                        continue
                    filtered.append(c)
                # Safety: 全 reject なら recover を残す
                if not filtered:
                    rec_keep = [c for c in all_cands if c.module == "RecoveryCandidate"]
                    if rec_keep:
                        filtered = [rec_keep[0]]
                all_cands = filtered
                self.stats.setdefault("n_sociable_pre_rejected", 0)
                self.stats["n_sociable_pre_rejected"] += pre_rejected_count
            except ImportError:
                pass
        
        if apply_canonical_dedup:
            try:
                from sociable_essence import CandidateCanonicalizer
                all_cands, n_removed = CandidateCanonicalizer.deduplicate(all_cands)
                self.stats.setdefault("n_sociable_dedup_removed", 0)
                self.stats["n_sociable_dedup_removed"] += n_removed
            except ImportError:
                pass
        
        return all_cands
    
    def select_best(self, state: WorldState,
                      conditions: Optional[Dict] = None,
                      map_layer: Optional[MAPLayer] = None
                      ) -> Tuple[Optional[FullCandidate], List[Tuple[FullCandidate, float]]]:
        """全候補生成 + merge + 最良返却"""
        all_cands = self.generate_all_candidates(state, conditions, map_layer)
        if not all_cands:
            return None, []
        
        scored = self.merger.merge(all_cands, state)
        return scored[0][0], scored
    
    def record_action_taken(self, action: Action):
        """invention pathway の試行カウント update"""
        self.invention.record_action(action)


# ============================================================
# Test
# ============================================================

if __name__ == "__main__":
    from chaotic_world import ChaoticWorld, ChaosConfig
    
    print("=" * 70)
    print("StrongEngineΩfull Test")
    print("=" * 70)
    
    rng = np.random.default_rng(42)
    eng = StrongEngineOmegaFull(rng=rng)
    
    # Test 1: 通常 state
    state = WorldState(t=0, R=60, E=70, G=70, O=65, K=50, X=25,
                         cumulative_score=0, is_ruined=False)
    
    print(f"\nNormal state (R=60, E=70, O=65, X=25):")
    conds = {"O_confidence": 0.8, "recent_drawdown": False, "true_veto": False,
              "reward_trend": 0.2, "recent_successful_action": ("invest", "A"),
              "score_trend": -0.05}
    best, scored = eng.select_best(state, conditions=conds)
    
    if best:
        print(f"  Best: {best.module}/{best.mode or '-'} -> "
              f"{best.attack_candidate.intent}/{best.attack_candidate.strength}")
        print(f"        score={scored[0][1]:.3f}, reason={best.reason}")
    print(f"  Total candidates: {len(scored)}")
    print(f"  Module breakdown: {eng.stats}")
    
    # Test 2: 危機 state (AggressiveEngine 抑制)
    eng2 = StrongEngineOmegaFull(rng=np.random.default_rng(43))
    state2 = WorldState(t=0, R=15, E=20, G=50, O=70, K=50, X=70,
                         cumulative_score=0, is_ruined=False)
    print(f"\nCrisis state (R=15, E=20, X=70):")
    best2, scored2 = eng2.select_best(state2, conditions=conds)
    if best2:
        print(f"  Best: {best2.module}/{best2.mode or '-'} -> "
              f"{best2.attack_candidate.intent}/{best2.attack_candidate.strength}")
    print(f"  Aggressive candidates: {eng2.stats['n_aggressive']} (should be 0)")
    
    # Test 3: AggressiveEngine 単独
    eng3 = StrongEngineOmegaFull(rng=np.random.default_rng(44))
    state3 = WorldState(t=0, R=70, E=70, G=70, O=80, K=50, X=30,
                         cumulative_score=0, is_ruined=False)
    print(f"\nGood state (R=70, O=80, X=30) - AggressiveEngine should activate:")
    agg_cands = eng3.aggressive.generate(state3, conditions=conds)
    print(f"  Aggressive candidates: {len(agg_cands)}")
    for c in agg_cands:
        print(f"    - {c.mode}: {c.attack_candidate.intent}/{c.attack_candidate.strength}, "
              f"safe={c.safe_variant.intent}/{c.safe_variant.strength}")
    
    print("\n[StrongEngineΩfull 動作確認 ✅]")
