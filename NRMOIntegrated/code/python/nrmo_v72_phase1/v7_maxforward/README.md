# NRMO v7 Realignment Package
## 設計者の構造訂正に基づく再配置 (StrongEngine Ω Full = 現実側)

### このパッケージの中身
```
NRMO_Realignment_Master_Spec.md     ★ 全修整の single source of truth
                                       (civ-sim→現実 の再配置マッピング)
NRMO_Constitution_v7_MaxForward.md     Max-Forward 憲法 (設計者意図)
engine/
  v7_two_layer.py    ★ 二層構造の正本 (現実 StrongEngine Ω Full + civ-sim MaxForward)
  v7_adapters.py        3 domain の DomainDynamics
  v7_engine.py          単層版 (参考)
  v7_validate.py        検証 harness
proof_1_store_domain_rollout.py      store 実証
proof_2_investment_domain_rollout.py investment 実証
proof_3_romance_domain_rollout.py    romance 実証
counter_civsim_rollout_fails.py      civ-sim 固定 rollout が破滅する反証
```

### 完了したこと
- **再配置原則の確立** — 全 component の civ-sim→現実 マッピング (Master Spec §1)
- **二層構造の中核実装** — 現実 StrongEngine Ω Full / civ-sim MaxForwardEngine / 双方向 bridge
- **3 domain 実証** — store 完璧 / investment 相場適応 / romance 倫理健全

### 未完了 (段階的に進める)
規模 (151+ Python, 90+ LaTeX, 複数 PDF, DecisionCompass) のため 1 回では完遂不能。
Master Spec §3-6 を指針に以下を段階実行する:
- Phase C: NRMO Integrated LaTeX の architecture 章修整 (ch20/ch_part9/vnext_plus/collective 等)
- Phase D: world_sim / collective_engine / vnext_plus の再接続
- Phase E: DecisionCompass の二層構造化
- Phase F: 全体統合 + PDF 再生成

### 正直な状態
1 セッションでの全修整は物理的に不可能。本パッケージは「設計図 (再配置原則書) +
中核コード + 実証」を提供し、残る修整を原則書に従って機械的に進められる基盤を作った。
全 component の実コード・全 LaTeX の書き換えは、ここから段階的に行う。
