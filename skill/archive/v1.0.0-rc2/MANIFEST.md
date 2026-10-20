# nrmo Skill — 試験対象の固定記録

| 項目 | 値 |
|---|---|
| 版 | **nrmo-skill v1.0.0-rc2**（候補版。正式版の承認は別判断） |
| 前版 | v1.0.0-rc1（`archive/v1.0.0-rc1/`、試験記録 `tests/2026-10-21/`） |
| パッケージ | `nrmo.skill` sha256 `ba3a13845dc3974a7a3a2539497bc0faa9f5acd833318eab3ff6e048c969fb0f` |
| ツリーハッシュ | 全ファイルの sha256 一覧の sha256：`1825fec6db4a17a7bf11b15178b50dc8992805571e61c20cb213aa121d2e2164` |
| 試験との一致 | rc2 試験で読み込ませた隔離設定内の Skill と `diff -r` で完全一致 |
| claude.ai 保存版 | **rc1 のまま**（rc2 は未保存）。アプリで試す場合は本パッケージを保存し直す |

## rc1 からの変更

変更は `SKILL.md` のみ。同梱資料（v7.3 正典、パッチ、ALB 文書ほか）は rc1 とハッシュ一致で、変更していない。

1. **モードと状態の表示規則**：4 層の決まり方を分けて表にした。Type ZERO は観測値（IRREV / VOL / LOAD）から §8.3 の規則で導けるときだけ割り当て、観測なし・一部のみ・矛盾の各場合は「未判定」とその理由を示す。本人の申告とこちらの解釈を区別する。Operational は「提案」、状態は「推奨」と明記する
2. **A_allowed と候補の整合**：候補 A・B・C は「今やってよい」の行動だけで組み立てる。保留・禁止の行動は候補に入れず、必要なら「条件付き候補（A_allowed の外）」として未充足条件と許容条件を書く。数字の出どころを「本人宣言」と「計算上の仮定」に分ける
3. **草稿の採用ルールが未決であることの扱い**：会話内の「確定扱いにして」を採用の決定とみなさない。選べる扱い（会話限定の仮適用／正式採用／適用しない）と影響を示し、選択は本人と明記する。選択が示されるまで草稿の規則を判定に使わない。**この振る舞いは暫定であり、採用ルールの決定ではない**（`tests/T3_ADOPTION_RULE_OPEN.md`）

## 同梱物と典拠

rc1 と同一（`archive/v1.0.0-rc1/MANIFEST.md` 参照）。

## ファイル別 sha256

```
bfe812f246b936ee6d6cc8cc0e2110015dd581f65d75fc7cde2acc945265bca9  nrmo/SKILL.md
a4f6942369a53981bddf95c65c2cdd73e1751f960b01c7d547201837844f1783  nrmo/references/NRMO_Integrated_System_v7_3.pdf
b3aca79494f3a9034a12555881a671b1d2db71c44eab3bb0fc35a4cb1af7eb91  nrmo/references/alb/ALB_THEORY_CH01_FOUNDATIONS_v0.2.md
3b7c93354d678b18ef2ac2f5925bfd412ce8740b90221cbbae477e7ad6b110d1  nrmo/references/alb/ALB_THEORY_CH02_FILL_v0.1.md
134b48380a4d8791b022b4db321224f9060b48a0927459b89f5747b22987804d  nrmo/references/alb/NRMO_ALB_ARCHITECTURE_v0.1.md
f130d1d223e3636f07206c98dbe1401364b5bd45e693918a3cae2a0079915c3c  nrmo/references/authority_boundaries.md
1e69f852a6f3acbd79666bd4f3c9299dc894b5b557c24f867ba104464153c97a  nrmo/references/evidence/CALIBRATION_REPORT.md
cd214965ddc77c708d58ab6d1582b31d1cea1ba4795c45db5157b3f13d69acc7  nrmo/references/evidence/DIAGNOSIS_over_defense.md
b05cf688d601cf5e145af3e9f93ab2adf74cc680acb27724dacdc3fb3b2b7c01  nrmo/references/evidence/EXPERIMENT_FINDINGS_Norn.md
2f96eebf0e4776a9542b7552f013f9527c58fafbe185cd1231a50fc570cb93ef  nrmo/references/evidence/PHASE11_COMPLETION_REPORT.md
d9adf4a88690ddcea01ff268fa69ee551dc0ba61993517c50bd63ee30c94a37e  nrmo/references/evidence/STRONG_ENGINE_OMEGA_FULL_REPORT.md
a771420765da1eef583f57e612253fd9800ecb6e0179887d3e1acdf63dc91a60  nrmo/references/ext_nonoverlap_v0_1.md
956dc4fbbd4b340ebf2ad9ab056e1e24bffe4cd95335b74fa8cc3b2a3056d21e  nrmo/references/foundations/DETECTION_INTERVENTION_PRINCIPLE.md
73e2794391a13b7b9ec4de198f1dae8659516b21c82a6aff3d2329c893cb3a89  nrmo/references/foundations/NRMO_Constitution_v7_MaxForward.md
d845845a1d93ff57343d0d40cde46b389a11c630b2d83b2fb2fb8634355cdd49  nrmo/references/foundations/NRMO_Realignment_Master_Spec.md
beefe8e610a657ec9c4c1d0c22be2bbe99376dc3584cf3c9b3a0604265fd85f2  nrmo/references/foundations/ch20_caged_beast.tex
474b635063830d12ec4065e6a13d77ab455af4bfef70e10e917a07948e85c712  nrmo/references/nrmo_system_v7_3.md
dbb79f8aeb4455031f598da7666608374fc7cbfcd0c8220629972b4b1705825d  nrmo/references/v7_3_patch.md
```

## 判断の分離

Skill の正式版承認、ALB 第2章の採用、PR #22 のマージ、T3 の採用ルールは、それぞれ本人の別判断として残す。本記録はいずれも含まない。
