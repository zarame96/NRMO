"""
core/typezero_proxy.py

TypeZero Proxy Layer (v8.3 で同時搭載)

役割:
  - 入力整形: objective, required_evaluation, output_policy
  - 出力整形: 結論 → 理由 → 選択肢 → 実行ステップ
  - 判断形式の安定化
  
非役割:
  - 数値評価の上書き
  - NRMO の VETO を上書き
  - StrongEngine の候補選択を変更
  - 人格模倣
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class TypeZeroPreprocessed:
    """TypeZero による入力整形結果"""
    objective: str
    required_evaluation: List[str] = field(default_factory=lambda: [
        "ruin_boundary",
        "reversibility",
        "allowed_actions",
        "risk_cap",
        "observation_metrics",
        "exit_conditions",
        "passive_pattern_check",
    ])
    output_policy: str = "conclusion_reason_options_steps"
    raw_context: Dict = field(default_factory=dict)


@dataclass
class TypeZeroFormattedOutput:
    """TypeZero による出力整形"""
    conclusion: str
    reason: str
    options: List[Dict]  # [{"label": "A", "description": "..."}]
    execution_steps: List[str]
    
    # Required fields (NRMO 出力の構造化)
    ruin_boundary: Optional[Dict] = None
    reversibility: Optional[Dict] = None
    risk_cap: Optional[Dict] = None
    observation_metrics: Optional[Dict] = None
    exit_conditions: Optional[List[str]] = None
    passive_pattern_check: Optional[Dict] = None
    
    def to_dict(self) -> Dict:
        return {
            "conclusion": self.conclusion,
            "reason": self.reason,
            "options": self.options,
            "execution_steps": self.execution_steps,
            "ruin_boundary": self.ruin_boundary,
            "reversibility": self.reversibility,
            "risk_cap": self.risk_cap,
            "observation_metrics": self.observation_metrics,
            "exit_conditions": self.exit_conditions,
            "passive_pattern_check": self.passive_pattern_check,
        }


class TypeZeroProxy:
    """TypeZero Proxy Layer"""
    
    def preprocess(self, user_input: Dict) -> TypeZeroPreprocessed:
        """入力整形
        
        user_input は context dict (e.g., {"situation": "..."})
        """
        objective = user_input.get("situation", "general_decision")
        
        return TypeZeroPreprocessed(
            objective=objective,
            raw_context=dict(user_input),
        )
    
    def postprocess(self, decision_payload: Dict) -> TypeZeroFormattedOutput:
        """出力整形
        
        decision_payload に含まれる必要なフィールド:
          - action
          - confidence
          - candidates (A/B/C 用)
          - trace (各 layer の判定)
          - veto_classification
          - passive_pattern_proposal (もしあれば)
        """
        action = decision_payload.get("action")
        confidence = decision_payload.get("confidence", 0.5)
        candidates = decision_payload.get("candidates", [])
        veto = decision_payload.get("veto_classification")
        pp = decision_payload.get("passive_pattern_proposal")
        
        # Conclusion
        if action is None:
            conclusion = "判断保留 (VETO または HOLD)"
        else:
            conclusion = f"推奨 action: {action.intent}/{action.strength} "\
                          f"(confidence {confidence:.2f})"
        
        # Reason
        reason_parts = []
        if veto and veto.veto_type.value != "no_veto":
            reason_parts.append(f"NRMO Core: {veto.veto_type.value} - {veto.reason}")
        if pp:
            reason_parts.append(
                f"PassivePattern level: {pp.level} (score {pp.score:.2f})"
            )
            if pp.has_correction_proposal:
                reason_parts.append(
                    f"PP correction proposed: {pp.proposal_reason}"
                )
        if not reason_parts:
            reason_parts.append("NRMO Core: approved, no veto")
        reason = "; ".join(reason_parts)
        
        # Options (A/B/C 提示)
        # candidates の上位 3 つ
        options = []
        for i, c in enumerate(candidates[:3]):
            options.append({
                "label": chr(ord("A") + i),
                "action": f"{c.intent}/{c.strength}",
                "description": f"{c.intent} ({c.strength} strength)",
            })
        
        # Execution steps
        if action:
            execution_steps = [
                f"Step 1: {action.intent} with strength {action.strength}",
                "Step 2: Observe state change (R, E, G, O, K, X)",
                "Step 3: Re-evaluate at next decision step",
            ]
        else:
            execution_steps = [
                "Step 1: Hold position",
                "Step 2: Gather information",
                "Step 3: Re-evaluate when situation changes",
            ]
        
        # Required fields
        ruin_boundary = None
        if veto and veto.ruin_boundary_breach:
            ruin_boundary = {
                "approached": True,
                "evidence": veto.falsifiable_evidence,
            }
        
        reversibility = None
        if action:
            reversibility = {
                "level": "high" if action.strength == "A" else (
                    "medium" if action.strength == "B" else "low"
                ),
            }
        
        passive_pattern_check = None
        if pp:
            passive_pattern_check = pp.to_dict()
        
        return TypeZeroFormattedOutput(
            conclusion=conclusion,
            reason=reason,
            options=options,
            execution_steps=execution_steps,
            ruin_boundary=ruin_boundary,
            reversibility=reversibility,
            passive_pattern_check=passive_pattern_check,
        )
