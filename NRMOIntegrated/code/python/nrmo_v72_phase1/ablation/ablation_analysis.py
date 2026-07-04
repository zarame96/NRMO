"""
NRMO v7.2 Phase 2 — Ablation Analysis

各機能の貢献度を定量化:
  - LOI effect = LOI condition - Baseline
  - LOO effect = Full - LOO condition (機能を抜くと減る分)
  - 機能採否判定 (Pareto + 効果サイズ)
"""
import os
import sys
import json
from pathlib import Path
from typing import Dict, List, Tuple
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
from ablation_engine import ALL_FEATURES

try:
    fm.fontManager.addfont('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc')
    plt.rcParams['font.family'] = 'Noto Sans CJK JP'
except Exception:
    pass
plt.rcParams['axes.unicode_minus'] = False


class AblationAnalyzer:
    """ablation 結果の解析"""
    
    def __init__(self, results_dir: str):
        self.results_dir = Path(results_dir)
        self.results = self._load_all()
        self.organized = self._organize()
    
    def _load_all(self) -> List[Dict]:
        results = []
        for f in sorted(self.results_dir.glob("*.json")):
            with open(f, "r") as g:
                results.append(json.load(g))
        return results
    
    def _organize(self) -> Dict:
        """{condition_id: {world: {horizon: cell}}} の構造化"""
        org = {}
        for r in self.results:
            cid = r["condition_id"]
            w = r["world"]
            h = r["horizon"]
            org.setdefault(cid, {}).setdefault(w, {})[h] = r
        return org
    
    def compute_effects(self, world: str, horizon: int,
                          metric: str = "median") -> Dict:
        """各機能の LOI/LOO 効果を計算
        
        LOI effect = LOI_X - BASELINE_v71
        LOO effect = FULL_v72 - LOO_X
        """
        if "BASELINE_v71" not in self.organized:
            return {}
        if "FULL_v72" not in self.organized:
            return {}
        
        baseline_val = self.organized["BASELINE_v71"][world][horizon]["stats"][metric]
        full_val = self.organized["FULL_v72"][world][horizon]["stats"][metric]
        
        effects = {
            "baseline": baseline_val,
            "full": full_val,
            "full_vs_baseline": full_val - baseline_val,
            "features": {},
        }
        
        for feature in ALL_FEATURES:
            loi_id = f"LOI_{feature}"
            loo_id = f"LOO_{feature}"
            
            loi_val = None
            loo_val = None
            
            if loi_id in self.organized:
                if world in self.organized[loi_id] and horizon in self.organized[loi_id][world]:
                    loi_val = self.organized[loi_id][world][horizon]["stats"][metric]
            
            if loo_id in self.organized:
                if world in self.organized[loo_id] and horizon in self.organized[loo_id][world]:
                    loo_val = self.organized[loo_id][world][horizon]["stats"][metric]
            
            effects["features"][feature] = {
                "loi_value": loi_val,
                "loo_value": loo_val,
                "loi_effect": (loi_val - baseline_val) if loi_val is not None else None,
                "loo_effect": (full_val - loo_val) if loo_val is not None else None,
            }
        
        return effects
    
    def feature_ranking(self, world: str, horizon: int,
                         metric: str = "median",
                         by: str = "loi_effect") -> List[Tuple[str, float]]:
        """機能を効果サイズでランキング"""
        effects = self.compute_effects(world, horizon, metric)
        ranked = []
        for feature, e in effects["features"].items():
            val = e.get(by)
            if val is not None:
                ranked.append((feature, val))
        ranked.sort(key=lambda x: x[1], reverse=True)
        return ranked
    
    def recommendation(self, world: str, horizon: int,
                         loi_threshold: float = 0.0,
                         loo_threshold: float = 0.0) -> Dict:
        """機能採否の推奨判定
        
        判定基準:
          - LOI effect > 0 (単独で改善)
          - or LOO effect > 0 (抜くと悪化 = 必須)
        """
        effects = self.compute_effects(world, horizon)
        recommendations = {}
        
        for feature, e in effects["features"].items():
            loi = e.get("loi_effect")
            loo = e.get("loo_effect")
            
            if loi is None or loo is None:
                recommendations[feature] = "UNKNOWN"
                continue
            
            if loi > loi_threshold and loo > loo_threshold:
                recommendations[feature] = "KEEP"  # 両方プラス
            elif loi > loi_threshold:
                recommendations[feature] = "LOI_ONLY"  # 単独で効果
            elif loo > loo_threshold:
                recommendations[feature] = "LOO_ONLY"  # 抜くと悪化
            elif loi < -0.5 and loo < -0.5:
                recommendations[feature] = "DROP"  # 両方マイナス
            else:
                recommendations[feature] = "NEUTRAL"
        
        return recommendations
    
    def print_summary(self, world: str, horizon: int):
        """サマリー出力"""
        effects = self.compute_effects(world, horizon)
        recs = self.recommendation(world, horizon)
        
        print(f"\n{'=' * 70}")
        print(f"Ablation Summary: {world} (H={horizon})")
        print(f"{'=' * 70}")
        print(f"Baseline (v7.1): {effects['baseline']:.3f}")
        print(f"Full (v7.2):     {effects['full']:.3f}")
        print(f"Full - Baseline: {effects['full_vs_baseline']:+.3f}")
        
        print(f"\n{'Feature':<8} {'LOI eff':>10} {'LOO eff':>10}  {'Rec':<10}")
        print("-" * 50)
        
        for feature in ALL_FEATURES:
            e = effects["features"].get(feature, {})
            loi = e.get("loi_effect")
            loo = e.get("loo_effect")
            rec = recs.get(feature, "?")
            
            loi_str = f"{loi:+.3f}" if loi is not None else "  N/A"
            loo_str = f"{loo:+.3f}" if loo is not None else "  N/A"
            
            print(f"{feature:<8} {loi_str:>10} {loo_str:>10}  {rec:<10}")
    
    def plot_ablation_heatmap(self, worlds: List[str], horizons: List[int],
                                 output_path: str, metric: str = "median",
                                 effect_type: str = "loi_effect"):
        """機能 × cell の効果ヒートマップ"""
        # データ収集
        cells = [(w, h) for w in worlds for h in horizons]
        matrix = np.full((len(ALL_FEATURES), len(cells)), np.nan)
        
        for j, (w, h) in enumerate(cells):
            effects = self.compute_effects(w, h, metric)
            for i, feature in enumerate(ALL_FEATURES):
                e = effects["features"].get(feature, {})
                val = e.get(effect_type)
                if val is not None:
                    matrix[i, j] = val
        
        # 可視化
        fig, ax = plt.subplots(figsize=(max(8, len(cells) * 1.2),
                                          max(10, len(ALL_FEATURES) * 0.4)),
                                facecolor='white')
        
        max_abs = np.nanmax(np.abs(matrix))
        if max_abs == 0 or np.isnan(max_abs):
            max_abs = 1
        
        im = ax.imshow(matrix, cmap='RdYlGn', aspect='auto',
                         vmin=-max_abs, vmax=max_abs)
        
        ax.set_xticks(range(len(cells)))
        ax.set_xticklabels([f"{w}\nH{h}" for w, h in cells], fontsize=9)
        ax.set_yticks(range(len(ALL_FEATURES)))
        ax.set_yticklabels(ALL_FEATURES, fontsize=9)
        ax.set_title(f"Ablation {effect_type} ({metric})",
                       fontsize=12, fontweight='bold')
        
        # 値表示
        for i in range(len(ALL_FEATURES)):
            for j in range(len(cells)):
                v = matrix[i, j]
                if not np.isnan(v):
                    color = 'white' if abs(v) > max_abs * 0.5 else 'black'
                    ax.text(j, i, f"{v:+.2f}", ha='center', va='center',
                              fontsize=8, color=color, fontweight='bold')
        
        plt.colorbar(im, ax=ax, label=f"{effect_type}")
        plt.tight_layout()
        plt.savefig(output_path, dpi=120, bbox_inches='tight', facecolor='white')
        plt.close()
        print(f"Saved: {output_path}")
    
    def plot_feature_ranking(self, world: str, horizon: int,
                              output_path: str, top_n: int = 22):
        """機能ランキング"""
        ranked_loi = self.feature_ranking(world, horizon, by="loi_effect")
        ranked_loo = self.feature_ranking(world, horizon, by="loo_effect")
        
        fig, axes = plt.subplots(1, 2, figsize=(14, 8), facecolor='white')
        
        for ax, ranked, title in [
            (axes[0], ranked_loi, f"LOI Effect ({world}, H={horizon})"),
            (axes[1], ranked_loo, f"LOO Effect ({world}, H={horizon})"),
        ]:
            ranked = ranked[:top_n]
            features = [r[0] for r in ranked]
            values = [r[1] for r in ranked]
            colors = ['#2ECC71' if v > 0 else '#E74C3C' for v in values]
            
            y_pos = np.arange(len(features))
            ax.barh(y_pos, values, color=colors)
            ax.set_yticks(y_pos)
            ax.set_yticklabels(features, fontsize=10)
            ax.invert_yaxis()
            ax.set_title(title, fontsize=12, fontweight='bold')
            ax.set_xlabel("Effect size")
            ax.axvline(x=0, color='black', linewidth=0.5)
            ax.grid(axis='x', alpha=0.3)
            
            for i, v in enumerate(values):
                ax.text(v, i, f" {v:+.3f}", va='center',
                          fontsize=9, fontweight='bold')
        
        plt.tight_layout()
        plt.savefig(output_path, dpi=120, bbox_inches='tight', facecolor='white')
        plt.close()
        print(f"Saved: {output_path}")


if __name__ == "__main__":
    analyzer = AblationAnalyzer("./ablation_results_quick")
    
    print(f"Loaded {len(analyzer.results)} cells")
    
    # Vulnerable サマリー
    analyzer.print_summary("Vulnerable", 200)
    
    # Normal サマリー
    analyzer.print_summary("Normal", 200)
    
    # 可視化
    output_dir = "./ablation_analysis"
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    analyzer.plot_ablation_heatmap(
        worlds=["Normal", "Vulnerable"],
        horizons=[200],
        output_path=f"{output_dir}/loi_heatmap.png",
        effect_type="loi_effect",
    )
    
    analyzer.plot_ablation_heatmap(
        worlds=["Normal", "Vulnerable"],
        horizons=[200],
        output_path=f"{output_dir}/loo_heatmap.png",
        effect_type="loo_effect",
    )
    
    analyzer.plot_feature_ranking("Vulnerable", 200,
                                    f"{output_dir}/ranking_vulnerable.png")
    analyzer.plot_feature_ranking("Normal", 200,
                                    f"{output_dir}/ranking_normal.png")
