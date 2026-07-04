"""
core/decision_trace.py

V8Engine の各レイヤー判定を記録する trace 機構。
監査指摘 (4. 受入基準: decision trace に各レイヤーの判定が残る) への対応。
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import json
import time


@dataclass
class TraceEntry:
    """1 レイヤーの判定記録"""
    layer: str
    timestamp_ms: float
    status: str  # "pass" | "warning" | "reject" | "info"
    data: Dict[str, Any] = field(default_factory=dict)
    notes: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            "layer": self.layer,
            "timestamp_ms": self.timestamp_ms,
            "status": self.status,
            "data": self._serialize(self.data),
            "notes": self.notes,
        }
    
    @staticmethod
    def _serialize(obj: Any) -> Any:
        """numpy / 複雑型を JSON serializable に変換"""
        try:
            import numpy as np
            if isinstance(obj, (np.bool_,)):
                return bool(obj)
            if isinstance(obj, np.integer):
                return int(obj)
            if isinstance(obj, np.floating):
                return float(obj)
            if isinstance(obj, np.ndarray):
                return obj.tolist()
        except ImportError:
            pass
        if isinstance(obj, dict):
            return {k: TraceEntry._serialize(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple, set)):
            return [TraceEntry._serialize(v) for v in obj]
        try:
            json.dumps(obj)
            return obj
        except (TypeError, ValueError):
            return str(obj)


@dataclass
class DecisionTrace:
    """V8Engine の 1 回の decide() 呼び出し全体の trace"""
    decision_id: int = 0
    start_time_ms: float = field(default_factory=lambda: time.time() * 1000)
    entries: List[TraceEntry] = field(default_factory=list)
    final_action: Optional[Any] = None
    final_status: Optional[str] = None  # "ACCEPT" | "REJECT" | "HOLD"
    rejection_reason: Optional[str] = None
    
    def add(self, layer: str, status: str, data: Dict, notes: Optional[str] = None):
        """新しいエントリを追加"""
        elapsed = time.time() * 1000 - self.start_time_ms
        self.entries.append(TraceEntry(
            layer=layer,
            timestamp_ms=elapsed,
            status=status,
            data=data,
            notes=notes,
        ))
    
    def reject(self, layer: str, reason: str, data: Optional[Dict] = None):
        """拒否を記録 (パイプライン早期終了)"""
        self.add(layer, "reject", data or {}, notes=reason)
        self.final_status = "REJECT"
        self.rejection_reason = f"{layer}: {reason}"
    
    def hold(self, layer: str, reason: str, data: Optional[Dict] = None):
        """HOLD を記録"""
        self.add(layer, "hold", data or {}, notes=reason)
        self.final_status = "HOLD"
        self.rejection_reason = f"{layer}: {reason}"
    
    def accept(self, action: Any):
        """採用を記録"""
        self.final_action = action
        self.final_status = "ACCEPT"
    
    def layer_status(self, layer: str) -> Optional[str]:
        """特定レイヤーの判定を取得"""
        for e in self.entries:
            if e.layer == layer:
                return e.status
        return None
    
    def layers_visited(self) -> List[str]:
        """到達したレイヤーの一覧"""
        return [e.layer for e in self.entries]
    
    def to_dict(self) -> Dict:
        return {
            "decision_id": self.decision_id,
            "final_status": self.final_status,
            "final_action": str(self.final_action) if self.final_action else None,
            "rejection_reason": self.rejection_reason,
            "layers_visited": self.layers_visited(),
            "total_duration_ms": (self.entries[-1].timestamp_ms 
                                    if self.entries else 0),
            "entries": [e.to_dict() for e in self.entries],
        }
    
    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)
    
    def summary(self) -> str:
        """人間可読サマリー"""
        lines = [
            f"DecisionTrace #{self.decision_id}",
            f"  Status: {self.final_status}",
        ]
        if self.rejection_reason:
            lines.append(f"  Reason: {self.rejection_reason}")
        lines.append(f"  Layers visited: {len(self.entries)}")
        for e in self.entries:
            marker = {
                "pass": "✓",
                "warning": "⚠",
                "reject": "✗",
                "hold": "⏸",
                "info": "·",
            }.get(e.status, "?")
            lines.append(f"    {marker} [{e.timestamp_ms:.1f}ms] {e.layer}: {e.status}")
            if e.notes:
                lines.append(f"        {e.notes}")
        return "\n".join(lines)


if __name__ == "__main__":
    # 動作確認
    trace = DecisionTrace(decision_id=1)
    trace.add("frame", "pass", {"status": "inside"})
    trace.add("falsifiability", "pass", {"triggered": False})
    trace.add("belief", "pass", {"entropy": 0.45})
    trace.add("shift", "warning", {"severity": 0.3})
    trace.add("cmdp", "pass", {"feasible": True})
    trace.add("gate", "warning", {"failed_gate": None}, "G6 borderline")
    trace.accept(action="invest_A")
    
    print(trace.summary())
    print()
    print("=== JSON ===")
    print(trace.to_json())
