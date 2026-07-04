"""
core/rng_manager.py

監査指摘 8 (乱数管理が不完全) への対応。
全コンポーネントに rng を注入し、グローバル np.random.* を排除。
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Optional
import numpy as np


@dataclass
class RNGLedger:
    """seed の系譜を記録"""
    master_seed: int
    derived: Dict[str, int]
    
    def to_dict(self) -> Dict:
        return {
            "master_seed": self.master_seed,
            "derived": dict(self.derived),
        }


class RNGManager:
    """乱数生成器の中央管理
    
    使い方:
      manager = RNGManager(master_seed=42)
      world_rng = manager.spawn("world")
      engine_rng = manager.spawn("engine")
      validation_rng = manager.spawn("validation")
    
    各 component は spawned rng を使い、グローバル np.random を呼ばない。
    """
    
    def __init__(self, master_seed: int = 42):
        self.master_seed = master_seed
        self.master_rng = np.random.default_rng(master_seed)
        self._ledger: Dict[str, int] = {}
    
    def spawn(self, name: str) -> np.random.Generator:
        """名前付き sub-rng を生成
        
        同じ name で 2 回呼んでも同じ rng が返るとは限らない (新規生成)。
        各 component は最初に 1 回 spawn して保持して使う。
        """
        # master から integer seed を生成
        sub_seed = int(self.master_rng.integers(0, 2**31 - 1))
        self._ledger[name] = sub_seed
        return np.random.default_rng(sub_seed)
    
    def get_ledger(self) -> RNGLedger:
        """全 spawn の系譜"""
        return RNGLedger(
            master_seed=self.master_seed,
            derived=dict(self._ledger),
        )
    
    def reset(self, master_seed: Optional[int] = None):
        """リセット (新規実験)"""
        if master_seed is not None:
            self.master_seed = master_seed
        self.master_rng = np.random.default_rng(self.master_seed)
        self._ledger = {}


if __name__ == "__main__":
    mgr = RNGManager(master_seed=42)
    
    world_rng = mgr.spawn("world")
    engine_rng = mgr.spawn("engine")
    validation_rng = mgr.spawn("validation")
    
    print("Sample from world_rng:", world_rng.integers(0, 100, 3).tolist())
    print("Sample from engine_rng:", engine_rng.integers(0, 100, 3).tolist())
    print("Sample from validation_rng:", validation_rng.integers(0, 100, 3).tolist())
    
    print("\nLedger:")
    ledger = mgr.get_ledger()
    print(f"  master: {ledger.master_seed}")
    for name, seed in ledger.derived.items():
        print(f"  {name}: {seed}")
    
    # 再現性確認
    print("\nReproducibility test:")
    mgr2 = RNGManager(master_seed=42)
    world_rng2 = mgr2.spawn("world")
    print("Sample from world_rng2:", world_rng2.integers(0, 100, 3).tolist())
    print("Should match world_rng above ✓")
