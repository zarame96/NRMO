"""
NRMO v7.2 Phase 3 — Combination Optimizer

22 機能の最適サブセット探索:
  Strategy 1: Greedy Forward Selection (機能を 1 つずつ追加)
  Strategy 2: Greedy Backward Elimination (全 ON から削減)
  Strategy 3: Simulated Annealing (ランダム摂動)
  
Phase 2 で「KEEP 9 機能」が発見されたので、それを seed として活用。
"""
import os
import sys
import json
import time
import random
from typing import List, Tuple, Optional, Dict
from dataclasses import dataclass, asdict
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'ablation'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from ablation_engine import FeatureFlags, ALL_FEATURES
from evaluator import CombinationEvaluator, EvaluationResult


@dataclass
class OptimizationStep:
    """1 ステップの記録"""
    step: int
    method: str  # "greedy_add", "greedy_remove", "sa_swap"
    flags_summary: str  # active features as string
    n_active: int
    composite_score: float
    pareto_violations: int
    total_improvement: float
    accepted: bool


class CombinationOptimizer:
    """機能サブセット最適化"""
    
    def __init__(self, evaluator: CombinationEvaluator):
        self.evaluator = evaluator
        self.history: List[OptimizationStep] = []
        self.best_flags: Optional[FeatureFlags] = None
        self.best_result: Optional[EvaluationResult] = None
        self.evaluation_count = 0
    
    def _record(self, step: int, method: str, flags: FeatureFlags,
                 result: EvaluationResult, accepted: bool):
        active = ",".join(f for f in ALL_FEATURES if getattr(flags, f))
        self.history.append(OptimizationStep(
            step=step,
            method=method,
            flags_summary=active[:80],
            n_active=result.n_active_features,
            composite_score=result.composite_score,
            pareto_violations=result.pareto_violations,
            total_improvement=result.total_improvement,
            accepted=accepted,
        ))
    
    def _update_best(self, flags: FeatureFlags, result: EvaluationResult):
        if (self.best_result is None or
            result.composite_score > self.best_result.composite_score):
            self.best_flags = FeatureFlags(**{
                f: getattr(flags, f) for f in ALL_FEATURES
            })
            self.best_result = result
            return True
        return False
    
    def _evaluate(self, flags: FeatureFlags) -> EvaluationResult:
        self.evaluation_count += 1
        return self.evaluator.evaluate(flags)
    
    def greedy_forward(self, initial: Optional[FeatureFlags] = None,
                         max_iterations: int = 30,
                         candidates: Optional[List[str]] = None) -> EvaluationResult:
        """Greedy Forward Selection: 機能を 1 つずつ追加"""
        print(f"\n{'=' * 60}")
        print(f"Greedy Forward Selection (max_iter={max_iterations})")
        print(f"{'=' * 60}")
        
        flags = initial or FeatureFlags.all_off()
        candidates = candidates or list(ALL_FEATURES)
        
        # 初期評価
        result = self._evaluate(flags)
        self._update_best(flags, result)
        step = 0
        self._record(step, "init", flags, result, True)
        print(f"  Step 0 (init): n_active={result.n_active_features}, "
                f"composite={result.composite_score:.3f}, "
                f"violations={result.pareto_violations}", flush=True)
        
        for iteration in range(max_iterations):
            step += 1
            # 現在 OFF の機能から、追加して最も改善する機能を選ぶ
            current_active = {f for f in ALL_FEATURES if getattr(flags, f)}
            candidates_to_try = [f for f in candidates if f not in current_active]
            
            if not candidates_to_try:
                print(f"  No more candidates", flush=True)
                break
            
            best_candidate = None
            best_score = result.composite_score
            best_candidate_result = None
            
            for cand in candidates_to_try:
                trial_flags = FeatureFlags(**{
                    f: getattr(flags, f) for f in ALL_FEATURES
                })
                setattr(trial_flags, cand, True)
                trial_result = self._evaluate(trial_flags)
                
                if trial_result.composite_score > best_score:
                    best_score = trial_result.composite_score
                    best_candidate = cand
                    best_candidate_result = trial_result
            
            if best_candidate is None:
                print(f"  Step {step}: No improvement found, stopping", flush=True)
                break
            
            # 採用
            setattr(flags, best_candidate, True)
            result = best_candidate_result
            self._update_best(flags, result)
            self._record(step, f"add_{best_candidate}", flags, result, True)
            
            print(f"  Step {step}: ADD {best_candidate} → "
                    f"n_active={result.n_active_features}, "
                    f"composite={result.composite_score:.3f}, "
                    f"violations={result.pareto_violations}", flush=True)
        
        return result
    
    def greedy_backward(self, initial: Optional[FeatureFlags] = None,
                         max_iterations: int = 30) -> EvaluationResult:
        """Greedy Backward Elimination: 機能を 1 つずつ削除"""
        print(f"\n{'=' * 60}")
        print(f"Greedy Backward Elimination (max_iter={max_iterations})")
        print(f"{'=' * 60}")
        
        flags = initial or FeatureFlags.all_on()
        
        result = self._evaluate(flags)
        self._update_best(flags, result)
        step = 0
        self._record(step, "init", flags, result, True)
        print(f"  Step 0 (init): n_active={result.n_active_features}, "
                f"composite={result.composite_score:.3f}", flush=True)
        
        for iteration in range(max_iterations):
            step += 1
            current_active = [f for f in ALL_FEATURES if getattr(flags, f)]
            
            if not current_active:
                break
            
            best_removal = None
            best_score = result.composite_score
            best_removal_result = None
            
            for cand in current_active:
                trial_flags = FeatureFlags(**{
                    f: getattr(flags, f) for f in ALL_FEATURES
                })
                setattr(trial_flags, cand, False)
                trial_result = self._evaluate(trial_flags)
                
                if trial_result.composite_score > best_score:
                    best_score = trial_result.composite_score
                    best_removal = cand
                    best_removal_result = trial_result
            
            if best_removal is None:
                print(f"  Step {step}: No improvement, stopping", flush=True)
                break
            
            setattr(flags, best_removal, False)
            result = best_removal_result
            self._update_best(flags, result)
            self._record(step, f"remove_{best_removal}", flags, result, True)
            
            print(f"  Step {step}: REMOVE {best_removal} → "
                    f"n_active={result.n_active_features}, "
                    f"composite={result.composite_score:.3f}", flush=True)
        
        return result
    
    def simulated_annealing(self, initial: FeatureFlags,
                              max_iterations: int = 30,
                              initial_temp: float = 1.0,
                              cooling_rate: float = 0.9) -> EvaluationResult:
        """Simulated Annealing: ランダム反転 + 受容判定"""
        print(f"\n{'=' * 60}")
        print(f"Simulated Annealing (max_iter={max_iterations}, T0={initial_temp})")
        print(f"{'=' * 60}")
        
        flags = FeatureFlags(**{f: getattr(initial, f) for f in ALL_FEATURES})
        result = self._evaluate(flags)
        self._update_best(flags, result)
        
        temp = initial_temp
        step = 0
        self._record(step, "init", flags, result, True)
        print(f"  Step 0: composite={result.composite_score:.3f}", flush=True)
        
        for iteration in range(max_iterations):
            step += 1
            # ランダムに 1 機能を反転
            cand = random.choice(ALL_FEATURES)
            trial_flags = FeatureFlags(**{
                f: getattr(flags, f) for f in ALL_FEATURES
            })
            setattr(trial_flags, cand, not getattr(trial_flags, cand))
            
            trial_result = self._evaluate(trial_flags)
            
            delta = trial_result.composite_score - result.composite_score
            
            # 受容判定 (Metropolis criterion)
            if delta > 0:
                accept = True
                reason = "improvement"
            else:
                accept_prob = np.exp(delta / max(temp, 0.001))
                accept = random.random() < accept_prob
                reason = f"random (p={accept_prob:.3f})"
            
            if accept:
                flags = trial_flags
                result = trial_result
                self._update_best(flags, result)
            
            self._record(step, f"sa_flip_{cand}", flags, result, accept)
            
            action = "FLIP" if accept else "STAY"
            sign = "+" if delta >= 0 else ""
            print(f"  Step {step}: {action} {cand} (T={temp:.3f}, "
                    f"Δ={sign}{delta:.3f}, {reason}) → "
                    f"composite={result.composite_score:.3f}", flush=True)
            
            temp *= cooling_rate
        
        return result
    
    def hybrid(self, max_iterations_each: int = 20):
        """Hybrid: Forward → Backward → SA"""
        print(f"\n{'=' * 60}")
        print(f"Hybrid Optimization")
        print(f"{'=' * 60}")
        
        # Phase A: Forward selection from empty
        forward_result = self.greedy_forward(
            initial=FeatureFlags.all_off(),
            max_iterations=max_iterations_each,
        )
        
        # Phase B: Backward elimination from best so far
        if self.best_flags:
            backward_result = self.greedy_backward(
                initial=self.best_flags,
                max_iterations=max_iterations_each,
            )
        
        # Phase C: SA from best
        if self.best_flags:
            sa_result = self.simulated_annealing(
                initial=self.best_flags,
                max_iterations=max_iterations_each,
            )
        
        return self.best_result
    
    def summary(self) -> Dict:
        if self.best_flags is None:
            return {}
        
        active = [f for f in ALL_FEATURES if getattr(self.best_flags, f)]
        return {
            "best_active_features": active,
            "n_active": len(active),
            "composite_score": self.best_result.composite_score,
            "pareto_violations": self.best_result.pareto_violations,
            "strict_improvements": self.best_result.strict_improvements,
            "total_improvement": self.best_result.total_improvement,
            "total_evaluations": self.evaluation_count,
            "cell_scores": self.best_result.cell_scores,
        }


if __name__ == "__main__":
    random.seed(42)
    
    # Evaluator 準備
    evaluator = CombinationEvaluator(
        worlds=["Normal", "Vulnerable", "FastExpansion"],
        horizons=[200],
        n_runs=80,
        n_workers=4,
    )
    evaluator.precompute_baseline()
    
    print(f"\nBaseline ready:")
    for k, v in evaluator.baseline_cache.items():
        print(f"  {k}: median={v['median']:.3f}")
    
    # Optimizer 実行
    optimizer = CombinationOptimizer(evaluator)
    
    # まず KEEP 9 機能を seed として Greedy Forward
    print("\n" + "=" * 60)
    print("Phase A: Greedy Forward from KEEP-9 seed")
    print("=" * 60)
    
    seed_flags = FeatureFlags.all_off()
    for f in ["I8", "I11", "H2", "G1", "G2", "G3", "G7", "G8", "G9"]:
        setattr(seed_flags, f, True)
    
    result = optimizer.greedy_forward(
        initial=seed_flags,
        max_iterations=15,
    )
    
    # Phase B: Backward 削除でさらに最適化
    if optimizer.best_flags:
        result = optimizer.greedy_backward(
            initial=optimizer.best_flags,
            max_iterations=15,
        )
    
    # 結果サマリー
    print("\n" + "=" * 60)
    print("OPTIMIZATION SUMMARY")
    print("=" * 60)
    summary = optimizer.summary()
    print(f"Best active features ({summary['n_active']}/22):")
    for f in summary['best_active_features']:
        print(f"  ✓ {f}")
    print(f"\nComposite score: {summary['composite_score']:.3f}")
    print(f"Pareto violations: {summary['pareto_violations']}")
    print(f"Total improvement: {summary['total_improvement']:+.3f}")
    print(f"Total evaluations: {summary['total_evaluations']}")
    
    # 結果保存
    with open("./optimization_result.json", "w") as f:
        json.dump(summary, f, indent=2)
    
    # History 保存
    with open("./optimization_history.json", "w") as f:
        json.dump([asdict(h) for h in optimizer.history], f, indent=2)
    
    print(f"\nSaved: optimization_result.json, optimization_history.json")
