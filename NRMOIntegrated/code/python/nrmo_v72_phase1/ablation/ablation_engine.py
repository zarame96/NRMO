"""
NRMO v7.2 Phase 2 — Ablation Engine

22 機能を個別 on/off できる V72Engine 拡張版:
  Invariants (5): I8, I9, I10, I11, I12
  HOLD (7): H1, H2, H3, H4, H5, H6, H7
  Gates (10): G1, G2, G3, G4, G5, G6, G7, G8, G9, G10
"""
import os
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
from enum import Enum
import numpy as np

# Phase 1 のモジュールをインポート
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))
from world_models import WorldState, Action
from engines import V71Engine, V72Engine, V72NewLayer, EngineOutput


# ============================================================
# Feature Flags
# ============================================================

class FeatureType(Enum):
    INVARIANT = "invariant"
    HOLD = "hold"
    GATE = "gate"


# 全 22 機能の ID
ALL_FEATURES = (
    # Invariants
    ["I8", "I9", "I10", "I11", "I12"] +
    # HOLD
    ["H1", "H2", "H3", "H4", "H5", "H6", "H7"] +
    # Gates
    ["G1", "G2", "G3", "G4", "G5", "G6", "G7", "G8", "G9", "G10"]
)


@dataclass
class FeatureFlags:
    """22 機能の on/off フラグ"""
    # Invariants
    I8: bool = True   # 推定値補正禁止
    I9: bool = True   # 範囲化義務
    I10: bool = True  # Vision 明示義務
    I11: bool = True  # レイヤー責任不可侵
    I12: bool = True  # 助言性明示義務
    
    # HOLD
    H1: bool = True   # 定義固定
    H2: bool = True   # Vision 明示
    H3: bool = True   # ベースレート可用性
    H4: bool = True   # ドメイン分類
    H5: bool = True   # スケール明示
    H6: bool = True   # 時間軸明示
    H7: bool = True   # 類似失敗履歴
    
    # Gates
    G1: bool = True   # 単位整合性
    G2: bool = True   # 内的一貫性
    G3: bool = True   # 物理上限
    G4: bool = True   # 出力形式
    G5: bool = True   # 桁妥当性
    G6: bool = True   # 不確実性単調性
    G7: bool = True   # 反例テスト
    G8: bool = True   # レイヤー越境
    G9: bool = True   # 助言性表示
    G10: bool = True  # 補正混入
    
    def __post_init__(self):
        pass
    
    @classmethod
    def all_off(cls) -> "FeatureFlags":
        """全機能 OFF (= v7.1 と等価)"""
        return cls(
            I8=False, I9=False, I10=False, I11=False, I12=False,
            H1=False, H2=False, H3=False, H4=False, H5=False, H6=False, H7=False,
            G1=False, G2=False, G3=False, G4=False, G5=False, G6=False,
            G7=False, G8=False, G9=False, G10=False,
        )
    
    @classmethod
    def all_on(cls) -> "FeatureFlags":
        """全機能 ON (= v7.2 full)"""
        return cls()
    
    @classmethod
    def loi(cls, feature_id: str) -> "FeatureFlags":
        """Leave-One-In: 指定機能のみ ON"""
        flags = cls.all_off()
        if hasattr(flags, feature_id):
            setattr(flags, feature_id, True)
        return flags
    
    @classmethod
    def loo(cls, feature_id: str) -> "FeatureFlags":
        """Leave-One-Out: 指定機能のみ OFF"""
        flags = cls.all_on()
        if hasattr(flags, feature_id):
            setattr(flags, feature_id, False)
        return flags
    
    def active_features(self) -> Set[str]:
        """ON の機能を返す"""
        return {f for f in ALL_FEATURES if getattr(self, f, False)}
    
    def summary(self) -> str:
        active = self.active_features()
        return f"Active: {len(active)}/22 features"


# ============================================================
# Ablatable V72 New Layer
# ============================================================

class AblatableV72NewLayer(V72NewLayer):
    """機能フラグで挙動を制御できる V72NewLayer"""
    
    def __init__(self, flags: Optional[FeatureFlags] = None):
        super().__init__()
        self.flags = flags or FeatureFlags.all_on()
    
    def _check_hold(self, state: WorldState) -> Dict:
        """HOLD Protocol — フラグで個別 on/off"""
        # H3 ベースレート可用性: 高 X で確率的 HOLD
        if self.flags.H3 and state.X > 75 and np.random.random() < 0.05:
            return {"should_hold": True, "type": "H3"}
        
        # H1 定義固定: 危機状態での即時 HOLD
        if self.flags.H1 and state.E < 20 and state.G < 20 and state.X > 70:
            return {"should_hold": True, "type": "H1"}
        
        # H2 Vision 明示: 状態の極端さ
        if self.flags.H2 and min(state.R, state.E, state.G) < 15:
            return {"should_hold": True, "type": "H2"}
        
        # H7 類似失敗履歴: 高リスク状態
        if self.flags.H7 and state.X > 80:
            return {"should_hold": True, "type": "H7"}
        
        # H4-H6 はシミュレーション内で常に充足想定
        
        return {"should_hold": False, "type": None}
    
    def _check_calibration_gate(self, state: WorldState, action: Action) -> Dict:
        """Calibration Gate — フラグで個別 on/off"""
        # G7 反例テスト: 高リスク + 強行動
        if self.flags.G7 and state.X > 60 and action.strength == "C":
            return {"all_passed": False, "failed_gate": "G7"}
        
        # G5 桁妥当性: 過剰投資検出
        if self.flags.G5 and state.R < 30 and action.intent == "invest" and action.strength != "A":
            return {"all_passed": False, "failed_gate": "G5"}
        
        # G2 内的一貫性: 体力低下時の探索矛盾
        if self.flags.G2 and state.E < 30 and action.intent == "explore":
            return {"all_passed": False, "failed_gate": "G2"}
        
        # G4 出力形式: 範囲化 (シミュ内では常に充足)
        # G10 補正混入: 暗黙補正なし (シミュ内では充足)
        
        # G1, G3, G6, G8, G9 はシミュ内で軽微な効果
        
        return {"all_passed": True, "failed_gate": None}
    
    def _compute_confidence(self, state: WorldState, action: Action, 
                            gate_result: Dict) -> float:
        """信頼度計算 — I9 (範囲化) が必要"""
        base = 0.7
        
        if self.flags.I9:  # I9 範囲化 OFF なら離散値で粗い
            base -= 0.05
        
        if not gate_result["all_passed"]:
            base -= 0.2
        
        health = (state.R + state.E + state.G) / 300
        base = base * 0.7 + health * 0.3
        base -= state.X / 200
        
        return max(0.0, min(1.0, base))


class AblatableV72Engine(V72Engine):
    """機能フラグで個別 ablation 可能な v7.2 Engine"""
    
    def __init__(self, flags: Optional[FeatureFlags] = None, delta: float = 0.01):
        # 親クラス初期化を経由せず、必要な属性を手動セット
        self.legacy = V71Engine()
        self.new_layer = AblatableV72NewLayer(flags or FeatureFlags.all_on())
        self.delta = delta
        self.flags = flags or FeatureFlags.all_on()
        
        self.selection_log = []
        self.use_new_count = 0
        self.use_legacy_count = 0
    
    def select_action(self, state: WorldState) -> Action:
        """Selector でアクション選択 (I11 レイヤー責任に従う)"""
        action_legacy = self.legacy.select_action(state)
        E_legacy = self._estimate_score(state, action_legacy)
        
        new_output = self.new_layer.select_action(state)
        action_new = new_output.action
        E_new = new_output.expected_score
        
        # I11 レイヤー責任: Selector が役割を厳格化
        # I8 補正禁止: 推定値そのまま使用 (補正なし)
        # I10 Vision 明示: シミュ内では暗黙的に Vision 充足
        # I12 助言性: 出力の最終マーカー追加 (シミュには影響なし)
        
        threshold = self.delta
        if self.flags.I8:
            # I8 ON のとき、補正なしの「中立推定」で比較
            pass  # 補正なしのまま
        else:
            # I8 OFF のとき、暗黙的に安全側補正
            E_new -= 0.02
        
        if E_new > E_legacy + threshold:
            self.use_new_count += 1
            self.selection_log.append("USE_NEW")
            return action_new
        
        self.use_legacy_count += 1
        self.selection_log.append("USE_LEGACY")
        return action_legacy


# ============================================================
# 動作確認
# ============================================================

if __name__ == "__main__":
    from world_models import World, WorldType
    
    print("=" * 60)
    print("Phase 2 — Ablation Engine 動作確認")
    print("=" * 60)
    
    # FeatureFlags の確認
    print("\n--- FeatureFlags ---")
    full = FeatureFlags.all_on()
    print(f"All ON: {full.summary()}")
    
    empty = FeatureFlags.all_off()
    print(f"All OFF: {empty.summary()}")
    
    loi_h3 = FeatureFlags.loi("H3")
    print(f"LOI H3: {loi_h3.summary()}, active={loi_h3.active_features()}")
    
    loo_g7 = FeatureFlags.loo("G7")
    print(f"LOO G7: {loo_g7.summary()}")
    
    # エンジンの動作確認
    print("\n--- Engine 動作確認 (Vulnerable, H=200, 30 runs) ---")
    
    for cond_name, flags in [
        ("All OFF (= v7.1)", FeatureFlags.all_off()),
        ("All ON (v7.2)", FeatureFlags.all_on()),
        ("LOI H3 only", FeatureFlags.loi("H3")),
        ("LOI G7 only", FeatureFlags.loi("G7")),
        ("LOO H3", FeatureFlags.loo("H3")),
        ("LOO G7", FeatureFlags.loo("G7")),
    ]:
        scores = []
        for seed in range(30):
            world = World(WorldType.VULNERABLE, seed=seed)
            engine = AblatableV72Engine(flags=flags)
            
            for t in range(200):
                action = engine.select_action(world.state)
                _, reward, done, _ = world.step(action)
                if hasattr(engine, 'update_reward'):
                    engine.update_reward(action, reward)
                if done:
                    break
            scores.append(world.state.cumulative_score)
        
        mean = np.mean(scores)
        median = np.median(scores)
        print(f"  {cond_name:25s}: mean={mean:6.2f}  median={median:6.2f}")
