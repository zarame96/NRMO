# loom100 開発履歴

dev_history/ の各版が、層ごとの構築段階のスナップショット。

- firm_ifrs_L0.bak : 基礎モデル（較正凍結前）
- firm_ifrs_L1.bak : 資本構成（社債/CB/自己株式/配当）
- firm_ifrs_L2.bak : 市場/競合
- firm_ifrs_L3.bak : イノベーション/新規事業
- firm_ifrs_L4.bak : 株価/企業理念（旧バリュエーション=実態固定）
- firm_ifrs_L5.bak : 操業レバー8種
- firm_ifrs_L6.bak : 業態転換
- firm_ifrs_pre_deaths.bak     : 死に方拡張の直前
- firm_ifrs_pre_growthcap.bak  : 成長資本機構の直前（株価エンジン作り直し・創業者・M&A・死に方は導入済）
- firm_ifrs_pre_ruinaversion.bak : 破滅回避特性の直前
- (現行 scripts/firm_ifrs.py) : 破滅回避・成長資本まで全て導入

各段階で会計恒等式（残差0）を直接測定で検証。NRMOエンジンは全段階で不可侵（無改変）。
