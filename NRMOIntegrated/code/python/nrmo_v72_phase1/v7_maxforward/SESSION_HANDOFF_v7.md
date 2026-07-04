# NRMO v7 セッション引き継ぎ書 (SESSION_HANDOFF)
## Max-Forward / 二層構造 / engine 配置の取り違え修正

作成日: 2026-05-29
最初に読むべき文書: **NRMO_Realignment_Master_Spec.md** (全修整の single source of truth)

---

## 0. このセッションの核心 (最重要)

```
【判明した根本誤り】
  これまで NRMO の engine 配置が逆だった:
    誤: StrongEngine Ω Full = civ-sim 側
    正: StrongEngine Ω Full = 現実側 (主役), MaxForwardEngine = civ-sim 側

【確立された原則 (Max-Forward)】
  ・default = 最大前進 (最低限/停滞ではない)
  ・NRMO は破滅成分だけ削る
  ・停滞は ruin として排除
  ・engine の rollout は対象 domain の真の dynamics で行う (内部 civ-sim 固定を排除)
  ・「最大前進 + 縁での方向転換」は rollout から創発させる

【「数値クソ」の根本原因 = 過度な防御】
  原因の二重構造: ①engine 配置の取り違え ②評価地平が短く成長を評価できない
  + minimum viable の誤り + 「停滞=安全」の誤読

【世界依存性 (重要 nuance)】
  「過度な防御」自体が悪ではない。世界次第で最善は変わる:
    store=攻撃最善 / 文明長期=持続成長最善 / V9 minimum=超慎重最善
  二層構造は最善を押し付けず、civ-sim が各世界の真の最善を探索する。
```

---

## 1. 二層構造 (正しい配置)

```
【現実側】StrongEngine Ω Full (v7_two_layer.py: StrongEngineOmegaFull)
  主役。あらゆる探索・推論・意思決定 (範囲無制限)。現実 domain の真の
  dynamics で最大前進。破滅は避ける。civ-sim に接続しない。Loom layer もここ。

【civ-sim 側】MaxForwardEngine (v7_two_layer.py: MaxForwardEngine)
  StrongEngine を模倣。死/破滅を許容 (フィードバック)。極端な慎重は排除。
  攻撃ピーク/防御ピークを算出し最善スコアを目指す。

【双方向】observe()/feedback() で現実 ⇄ civ-sim が情報蓄積。
```

---

## 2. 完了した成果物 (場所: /mnt/user-data/outputs/NRMO_v7_MaxForward/)

```
文書:
  NRMO_Realignment_Master_Spec.md   ★ 全修整の指針 (§1再配置表/§3-4修整指針/§8 collective)
  NRMO_Constitution_v7_MaxForward.md   Max-Forward 憲法 (5原則)
  DIAGNOSIS_over_defense.md            過度な防御 + 世界依存性
  README.md                            パッケージ全体説明

コード (engine/):
  v7_two_layer.py    ★ 二層構造の正本 (MaxForwardEngine + StrongEngineOmegaFull + bridge)
  v7_adapters.py        store/investment/romance の DomainDynamics (action_spectrum 付き)
  v7_civ_dynamics.py    文明 domain (CivilizationDynamics)
  v7_engine.py          単層版 (参考)
  v7_validate.py        検証 harness

実証:
  proof_1_store / proof_2_investment / proof_3_romance / counter_civsim_rollout_fails

パッケージ: /mnt/user-data/outputs/NRMO_v7_Realignment_Package.zip
```

---

## 3. 検証結果 (確定済み・再現可能)

```
store      : ruin 0%, surv 300, revenue 6825 (完璧)
investment : equity 相場適応 0.30-0.51, 下落/回復で buyhold 超え, fat_tail 27-38% ruin (課題)
romance    : active_ruin 0%, clean 93-96% (倫理健全, success は相手依存)
文明        : 長期評価(horizon100)で g=0.30 持続成長が最善, 短期(12)だと防御に倒れる
反証        : civ-sim 固定 rollout を store に使うと defend/B 選択で破滅 (counter_*.py)
```

---

## 4. 残作業 (Phase C-F, 原則書 §3-8 が指針)

```
Phase C: LaTeX architecture 章の修整 (現実側として書き換え)
  対象: ch20_strong_engine.tex, ch_part9_omega_full.tex,
        ch_part_xiii_v63_vnext_plus.tex, ch_part_xiii_v70_collective.tex,
        ch27_time_horizon.tex, ch30_success_definitions.tex, ch_part12_methodology.tex
  指針: 原則書 §3 の表。新章「二層構造」を追加。
  場所: /tmp/v72/integrated_v72/chapters/ (要再展開: uploads/NRMO_Integrated_System_v7_2_source.zip)

Phase D: collective_engine 実コード再接続
  対象: world_sim_v50/src/collective_engine_v71.py (CollectiveStrongEngine が核心),
        nrmo_collective_v70.py
  指針: 原則書 §8。CollectiveStrongEngine=現実側, 集団 MaxForward=civ-sim 側,
        shock予測→縁検出, triage→方向転換, 長期評価必須。

Phase E: DecisionCompass の二層構造化
  対象: /mnt/user-data/outputs/DecisionCompass_*.py, (local) decision_compass
  指針: 原則書 §5。nrmo_core を二層構造に接続。

Phase F: 全体統合 + PDF 再生成
  全 Python/LaTeX を統合し NRMO Integrated PDF を再生成。
```

---

## 5. 再現方法 (次セッションで環境を復元)

```bash
# 元 model の展開 (uploads から)
cd /tmp && mkdir v6_repaired && cd v6_repaired
unzip /mnt/user-data/uploads/NRMO_v6_Repaired_Canonical_20260529.zip
# → StoreOperationAdapter: code/python/nrmo_universal_adapter.py
# → OmegaFullEngine 本体: world_sim_v50/src/vnext_plus.py

# Bundle (元 model: store/investment/romance + harness)
cd /tmp && mkdir vbundle && cd vbundle
unzip /mnt/user-data/uploads/NRMO_v6_to_v6_1_Claude_Complete_Bundle_20260529.zip
# → investment: packages/inv/investment_stress_models.py
# → romance:    packages/rom/nrmo_romance_hardhit_20260529/romance_simulation_harness.py

# v6.1 profile (比較用)
cd /tmp && mkdir v61_ext && cd v61_ext
unzip /mnt/user-data/uploads/NRMO_v6_1_Implemented_Profile_20260529.zip

# v7.2 source (LaTeX 修整対象)
cd /tmp && mkdir v72 && cd v72
unzip /mnt/user-data/uploads/NRMO_Integrated_System_v7_2_source.zip

# 検証 (二層構造の動作確認)
 cd <package>  # または outputs/NRMO_v7_MaxForward/engine/ から
python3 v7_validate.py            # 単層 3 domain
python3 v7_civ_dynamics.py        # 文明 domain 二層構造
```

---

## 6. 次セッション開始手順

```
1. この引き継ぎ書と NRMO_Realignment_Master_Spec.md を最初に渡す
2. §5 で環境復元 (元 model 展開)
3. Phase C (LaTeX) か Phase D (collective 実装) から着手
4. 各成果は原則書に照合し、過度な防御に倒れていないか確認
```

---

## 7. 繰り返してはいけない誤り (取り違えの履歴)

```
× StrongEngine Ω Full を civ-sim engine と扱う → 保守化 → 破滅
× engine 内部に civ-sim dynamics を固定 → domain と乖離 → 数値クソ
× 「最低限の前進 (minimum viable)」を選ぶ → 停滞 → passive death
× 「停滞=安全」とみなす → 過度な防御
× 評価地平を短くする → 成長を評価できず防御に倒れる
× 「過度な防御=常に悪」と単純化 → 世界依存性 (V9 minimum) を見落とす
```

---

## 8. ユーザー (設計者) について
- NRMO の創造者・設計者。日本語のみ。省略禁止、honest 報告。
- 設計者の本来の意図 > 凍結された憲法 (相違あれば憲法を書き換える権限を行使済み)。
- 個人状況には自発的に触れない。

---

## 9. Phase C 進捗 (LaTeX 修整)

```
[完了] ch20_strong_engine.tex
  挿入節「v7 Realignment: Real-Side Primacy and Two-Layer Structure」
  - Real side = Strong Engine Ω Full (主役, 最大前進, Loom もここ)
  - civ-sim side = MaxForwardEngine (模倣, 極端探索, 双方向)
  - World-dependence (世界依存性, V9 minimum 含む)
  - Rollout discipline (rollout は真の dynamics で, 短い地平=過度な防御)
  保存先: latex_patches/ch20_strong_engine.tex

[残り Phase C] 同じ要領で以下を修整:
  ch_part9_omega_full.tex      → Ω Full を現実 domain の最大前進 engine として
  ch_part_xiii_v63_vnext_plus.tex → vnext_plus を現実側 engine 実装として
  ch_part_xiii_v70_collective.tex → collective を現実側集団動態として
  ch27_time_horizon.tex        → 評価地平 (長期必須, 短期=過度な防御) を明記
  ch30_success_definitions.tex → 現実=破滅回避最大前進 / civ-sim=ピーク探索
  ch_part12_methodology.tex    → 二層構造の方法論
各章の冒頭付近に同様の \section{v7 Realignment...} を挿入するのが定石。
```

---

## 10. Phase C 完了 (2026-05-29 更新)

```
[完了] LaTeX architecture 章 全 7 章に v7 Realignment note を挿入:
  ✓ ch20_strong_engine        (現実側主役 + 二層構造 + 世界依存性 + rollout discipline)
  ✓ ch_part9_omega_full       (Ω Full = 現実 domain 最大前進 engine)
  ✓ ch27_time_horizon         (★評価地平と過度な防御: horizon12→防御/horizon100→成長)
  ✓ ch30_success_definitions  (現実=最大前進 / civ-sim=ピーク探索)
  ✓ ch_part12_methodology     (二層構造の方法論)
  ✓ ch_part_xiii_v63_vnext_plus  (現実側 engine 実装)
  ✓ ch_part_xiii_v70_collective  (現実側集団動態)
  保存: latex_patches/*.tex (7 ファイル)

[完了] Phase A–F 全完了:
  Phase D [完了 2026-05-30] collective_engine 実コード接続 → §11 参照
  Phase E [完了 2026-05-30] DecisionCompass 二層構造化 → §12 参照
  Phase F [完了 2026-05-30] 統合 + PDF 再生成 (511p) → §13 参照
```

---

## 11. Phase D 完了 (2026-05-30)

```
[完了] collective_engine_v71.py の実 CollectiveStrongEngine を二層構造の
       現実側として接続。成果物: engine/v7_collective_two_layer.py
       詳細報告: PHASE_D_REPORT.md

  現実側  = CollectiveStrongEngineRealSide (実 CollectiveStrongEngine 保持,
            forecast_next_shock で縁検出, 平時=最大前進/縁=triage方向転換)
  civ-sim = CollectiveMaxForwardEngine (真の集団 dynamics・長期地平で
            攻撃↔防御 spectrum を試行, ピーク/最善を算出)
  ★第4原則: 実 engine 内部の軽量固定 _rollout_collective を排除し、
            スコアを civ-sim の真 dynamics・長期地平に置換。

  検証 (python3 engine/v7_collective_two_layer.py, NRMO_V6_SRC 要設定):
    [A] 実 select_configuration 実行 OK (n_admissible=25)
    [B] 世界依存性: 穏やか→攻撃最善 / fat-tail→保険込み(a=0.25)最善 (V9-minimum)
    [C] ★地平の向きは domain 構造依存★: 集団保険 domain は 短期→攻撃/長期→防御 で
        §8/文明 (短期→防御/長期→成長) と逆。過度な調整はせず正直に明記。
    [D] 現実側二層: ruin 標準5%/fat-tail2%, 方向転換率 50%/63% (世界依存)

  正直な残課題: 残留 tail ruin (単発巨大 shock の一撃破滅, 投資 fat_tail と同種だが低い),
              CollectiveDomainDynamics は合成代理 (実 population step 接続は Phase F)。
```

---

## 12. Phase E 完了 (2026-05-30)

```
[完了] DecisionCompass を二層構造の正本として再構築 (前セッション分は環境リセットで消失)。
       成果物: engine/v7_decision_compass.py  詳細報告: PHASE_E_REPORT.md

  実コード3点を結合:
    憲法境界(Loom) = 実 nrmo_core.construct_admissible_set (governance veto only)
    真の dynamics  = 実 civstate_transition / is_ruin_state (第4原則)
    engine         = v7 二層 (StrongEngineOmegaFull + MaxForwardEngine)
  CivState(R,E,G,O,K,X) を「個人の状況」として再解釈。

  ★gov-exec 分離 (不可侵) を構造的に保証: A_t=NRMO(X_t), a_t=Engine(A_t)。
   _Restricted wrapper で engine に admissible set だけを渡し override 不可。

  検証 (python3 engine/v7_decision_compass.py, NRMO_V6_ROOT 要設定):
    [A] リスクで admissible 縮小: 健全3/5 ALLOW, 過熱2/5 ALLOW, 縁5/5 EXIT_HOLD
    [B] engine 選択は admissible 内 (veto override 不可) を実証
    [C] 軌道 200step: ruin 0%, 最大前進継続

  正直な所見: 推奨が慎重寄り(g=0.18)に出るのは、実 dynamics で高成長が暴露Xを上げ
            前進量(R+E+G+O+K−X)を下げるため。停滞ではなく世界依存性(V9-minimum的)。
            攻撃側を削ったのは governance であり engine ではない。暴露重みは既存
            v7_civ_dynamics と同規約。過度な調整を避け実出力をそのまま報告。
```



---

## 13. Phase F 完了 (2026-05-30)

```
[完了] 全体統合 + NRMO Integrated PDF 再生成。詳細: PHASE_F_REPORT.md
       成果物: NRMO_Integrated_System_v7_2_rev2_EN.pdf (511ページ, 英語のみ)

  ・latex_patches の 7 章を v7.2-rev2 source の chapters/ に上書き
  ・Phase D/E の成果を本文に英語節として統合
    (collective章末=Phase D, ch20末=Phase E。latex_patches にも反映済)
  ・pdflatex 多パスで再生成。v7 Realignment 節8箇所, Two-Layer言及15箇所。

  英語のみ化 (English-only): 当初の CJK エラーは英語散文でなく master 取り込み
    ファイルの残留日本語が原因だった。4箇所を英訳/ローマ字化 (latex_english_only_fixes/):
    final_build_statement(モットー英訳), v52_to_v62(文明名グロス削除),
    world_simulation_vision(宗族→zōngzú,科挙→kējǔ,鎖国→sakoku,一向一揆→Ikkō-ikki 等)。
    結果: CJK Unicode エラー 0 / 出力PDF内CJK文字 0。完全英語。
  既存残課題(Phase F由来でない): Illegal pream-token(C) 42件(未定義列型,要\newcolumntype),
    undefined ref 6件(source既存プレースホルダ)。

[全 Phase 完了] A 原則書 / B 中核コード / C LaTeX7章 / D collective実接続 /
              E DecisionCompass二層化 / F 統合+PDF再生成。
```

---

## 14. StrongEngine Ω Full — 訂正 + 本物駆動検証 (2026-05-30)

```
[訂正] 前版で作った engine/strong_engine_omega_full.py は本物と同名の薄いスタブで
       Wolf/Shinobi/MAPLayer/Norn-Skuld 名を騙っていた。誤り。削除した。

[正] 本物の完全実装は code/python/nrmo_v72_phase1/core/ に存在:
     strong_engine_omega_full(Aggressive: Wolf Pursuit 等), shinobi_engine
     (Norn/Skuld + 12 units + Thompson 防御/race), map_layer(L1/L2/L3 V-Cache),
     loom_engine(sparse 決定境界), unified_engine(統合)。

  engine/omega_full_integrated.py: 本物をそのまま駆動し各サブシステムの発火を実証。
    Wolf 生成2/採用1, aggressive 全mode, MAPLayer L1/L2/L3=5/10/41 regime_shift=28,
    Shinobi 12units・Norn 10/10・Thompson 両learner, Loom 69決定 → 生存10/10 PASS。
    本物自身の validation/test_v8_integrity.py も 14/14 PASS。

  engine/separation_engine.py: NRMO 分離契約の汎用参照 (本物の名前は騙らない)。
  engine/run_all_validations.py: Part A 本物10 + Part B 分離契約8 = ALL PASS。
  engine/nrmo_separation_realcheck.py: 実 nrmo_core filter 接続, ruin=0/admissible違反0。

  実行: NRMO_V6_CORE=.../nrmo_v72_phase1/core python3 engine/run_all_validations.py
  報告: STRONG_ENGINE_OMEGA_FULL_REPORT.md (訂正版)
```

---

## 15. Core 未実装/partial の修正 (2026-05-30)

```
監査で挙げた現役コードの partial を実装。詳細: core_fixes/CORE_FIXES_REPORT.md
patched: core_fixes/{cumulative_risk_tracker, loom_core, loom_engine, falsifiability}.py

  #1 loom_core cumulative_exposure 配線:
     CumulativeRiskTracker.exposure_scalar() 追加 → RiskState.evaluate →
     LoomCore.decide_weaving → _compose_weaving で消費 (高暴露で caution escalation)。
     LoomEngine が scalar を注入。死にフィールド (常時0.0/未読) を実信号化。
  #3 falsifiability.is_triggered 実装 (NotImplementedError 解消):
     _default_failure_detect で検出規約統一, monitor も is_triggered へ委譲。

  検証: #1 exposure 0→1 配線&消費確認, #3 monitor 自動検出, 回帰 test_v8_integrity 14/14。
        本物サブシステム駆動 omega_full_integrated も ALL ALIVE 維持。
  未対応(理由付): v8_engine placeholder(実験engine), investment/romance(別bundle),
                v7 proxy(実domain接続は別作業)。
```

### 15b. Loom 実装 完全性監査 (2026-05-30)
```
Q「Loom の実装は完璧か」精査:
  完全: weaving 全7 Context+drifting+default 網羅, cooldown/priority/fallback/
        suppression 実装, Loom系8ファイルに空スタブ/TODO 無し(__main__ self-test除く),
        loom_v3 系は projected_breach_after で累積 risk を revalidation gate 消費。
  修正: loom_core cumulative_exposure を配線+weaving消費。当初 escalation が
        OPPORTUNITY/STAGNATION の cap=B に上書きされる整合バグ → decide_weaving 後の
        hard clamp に変更し全context で cap=A+AGGR抑制を保証 (検証済)。
  非完璧(正直): Loom が複数系統に分岐(loom_core系 / v3系 / engine_v2)し正典が単一に
        pin されていない(整理課題, correctness欠陥ではない); 累積消費機構が系統間で
        不統一(loom_core=強度clamp / v3=revalidation veto)。
```

### 15c. 最大前進「C」解禁 (loom_core, 2026-05-30)
```
Ω Full×最大前進に適合する Loom = loom_core (前進系thread全保有)。
従来 opportunity 上限 "B" → verified-safe かつ強い opportunity のみ "C"(全力Wolf Pursuit)解禁。
  gate: R>=70,X<=40,not r_low/critical,not drawdown,cum<0.30,world∉{drifting,chaotic},
        O>=60,ruin_proximity<=0.05 → cap="C",AGGRESSIVE0.80,MUTATION0.40。
  backstop: 累積clamp(cum>=0.7→A)/drift override/cap ceiling/下流veto。
  検証: safe→C, X高R低→B, 累積高→A, chaotic→B; 回帰14/14, 本物ALL ALIVE。
patched: core_fixes/loom_core.py
```
