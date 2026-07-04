"""
Loom 正典指定 (canonical pin) — 2026-05-30。
v7.2 version_manifest の経験的結論に整合。

正典:
  CANONICAL_LOOM_CORE   = loom_core.LoomCore
      production の上位制御核。v851_engine / unified_engine が直接使用。
      Ω Full の前進系 thread (AGGRESSIVE/MUTATION/INVENTION/EXPLORATION) を全保有。
      verified-safe かつ強い opportunity でのみ最大前進 C を解禁 (多重 backstop 付)。
      → 「Ω Full × 最大探索/前進」に適合する正典 Loom 制御核 (Zarame 指示)。

  CANONICAL_LOOM_ENGINE = loom_v3_1_shadow.LoomV31Shadow
      standalone Loom-engine の運用アイデンティティ = Loom v3.1 (凍結 Behavioral Core,
      canonical 3x3 benchmark で 9/9 cell が Top-3) + Sociable Shadow Layer
      (観測のみ・default ON・score 影響ゼロを paired-diff で検証)。
      ★ v3.2 / v3.2.1(tuned) は negative result (Detection≠Intervention を裏付け) のため
        正典ではなく archived。v3.1 凍結が経験的結論。

archived (歴史的・被置換 or negative result):
  loom_engine, loom_engine_v2, loom_v3, loom_v3_2, loom_v3_2_tuned
frozen-core (CANONICAL_LOOM_ENGINE の母体):
  loom_v3_1  (Loom v3.1 Behavioral Core, 凍結)

注: 2系統は役割が異なり共存する。
  - loom_core      = Ω Full 制御核 (production 数値エンジン v851/unified 用, 前進最大化)
  - loom_v3_1_shadow = standalone Loom 運用アイデンティティ (chaotic/drift survival, 凍結+観測)
"""
from loom_core import LoomCore, LoomLayer, Thread   # 正典 core re-export

CANONICAL_LOOM_CORE = "loom_core.LoomCore"
CANONICAL_LOOM_ENGINE = "loom_v3_1_shadow.LoomV31Shadow"
FROZEN_BEHAVIORAL_CORE = "loom_v3_1.LoomV31"
ARCHIVED_LOOM = [
    "loom_engine", "loom_engine_v2", "loom_v3",
    "loom_v3_2", "loom_v3_2_tuned",          # v3.2/v3.2.1 = negative result
]
__all__ = ["LoomCore", "LoomLayer", "Thread", "CANONICAL_LOOM_CORE",
           "CANONICAL_LOOM_ENGINE", "FROZEN_BEHAVIORAL_CORE", "ARCHIVED_LOOM"]
