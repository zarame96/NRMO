# nrmo Skill — 試験対象の固定記録

| 項目 | 値 |
|---|---|
| 版 | **nrmo-skill v1.0.0-rc1**（試験前の候補版。合否は別判断） |
| 作成 | 2026-10-21 |
| パッケージ | `nrmo.skill` sha256 `164abcf3063495ee98201720c6f4374ae0977dc50aaa6a8aa75416669e3284bf` |
| ツリーハッシュ | 全ファイルの sha256 一覧の sha256：`2be1b12cbb98efd4bf78f1995cbbfc673b1fdf96a906ac567b391a707f630ab5` |
| 導入済み版との一致 | claude.ai に保存された `nrmo`（synced）と `diff -r` で完全一致を確認 |
| 典拠の版 | NRMO `992e16d`（main）＋本 PR ブランチ、DecisionCompass `4b01b67` |

## 同梱物と典拠

| ファイル | 典拠 | 一致確認 |
|---|---|---|
| `references/nrmo_system_v7_3.md` | `NRMOIntegrated/source/v7.3/original/NRMO SYSTEM_7.3.md` | sha256 一致 |
| `references/v7_3_patch.md` | `NRMOIntegrated/source/v7.3/original/NRMO_SYSTEM_v7_3_PATCH.md` | sha256 一致 |
| `references/authority_boundaries.md` | `NRMOIntegrated/docs/AUTHORITY_BOUNDARIES.md` | sha256 一致 |
| `references/ext_nonoverlap_v0_1.md` | `NRMOIntegrated/docs/EXT_NONOVERLAP_v0_1.md` | sha256 一致 |
| `references/NRMO_Integrated_System_v7_3.pdf` | `NRMOIntegrated/NRMO_Integrated_System_v7_3.pdf`（537p） | sha256 一致 |
| `references/foundations/ch20_caged_beast.tex` | `NRMOIntegrated/chapters/ch20_strong_engine.tex` | sha256 一致 |
| `references/foundations/NRMO_Realignment_Master_Spec.md` ほか 2 件 | DecisionCompass `nrmo_v72_phase1/` | 複製 |
| `references/evidence/` 5 件 | DecisionCompass / NRMO `research/loom100` | 複製 |
| `references/alb/` 3 件 | `ALB/` | sha256 一致 |

## ファイル別 sha256

```
5c537e9f611b432d541614897975671fd450a078d32365f85f077a86f2c9bcd4  nrmo/SKILL.md
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

Skill の試験合格、ALB 第2章の採用、PR のマージは、それぞれ別の判断として扱う。本記録はいずれの判断も含まない。
