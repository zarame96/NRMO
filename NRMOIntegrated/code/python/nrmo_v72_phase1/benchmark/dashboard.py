"""
NRMO v7.2 Phase 1 — Visualization Dashboard

ベンチマーク結果を可視化:
  - エンジン × ワールド × ホライズン のヒートマップ
  - Score 分布
  - Pareto 改善検証
  - 統計検定結果サマリー
"""
import sys
import os
from pathlib import Path
from typing import Dict, List, Optional
import json
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

# 日本語フォント設定 (環境依存)
try:
    fm.fontManager.addfont('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc')
    plt.rcParams['font.family'] = 'Noto Sans CJK JP'
except Exception:
    pass
plt.rcParams['axes.unicode_minus'] = False


class BenchmarkDashboard:
    """ベンチマーク結果の可視化"""
    
    def __init__(self, checkpoint_dir: str):
        self.checkpoint_dir = Path(checkpoint_dir)
        self.all_results = self._load_all()
    
    def _load_all(self) -> List[Dict]:
        results = []
        for f in sorted(self.checkpoint_dir.glob("*.json")):
            with open(f, "r") as g:
                results.append(json.load(g))
        return results
    
    def _organize(self) -> Dict:
        """{engine: {world: {horizon: cell}}} 形式に整理"""
        organized = {}
        for r in self.all_results:
            engine = r["engine"]
            world = r["world"]
            horizon = r["horizon"]
            organized.setdefault(engine, {}).setdefault(world, {})[horizon] = r
        return organized
    
    def plot_score_heatmap(self, output_path: str, metric: str = "median"):
        """Score ヒートマップ (engine × world × horizon)"""
        organized = self._organize()
        engines = sorted(organized.keys())
        
        # World と Horizon を収集
        all_worlds = set()
        all_horizons = set()
        for e in engines:
            for w in organized[e]:
                all_worlds.add(w)
                all_horizons.update(organized[e][w].keys())
        
        worlds = sorted(all_worlds)
        horizons = sorted(all_horizons)
        
        # サブプロット: 1 行 × engines 列
        fig, axes = plt.subplots(1, len(engines), 
                                  figsize=(5 * len(engines), 6),
                                  facecolor='white')
        if len(engines) == 1:
            axes = [axes]
        
        # 全 engine 共通の color scale を計算
        all_values = []
        for e in engines:
            for w in worlds:
                for h in horizons:
                    if w in organized[e] and h in organized[e][w]:
                        all_values.append(organized[e][w][h]["stats"][metric])
        
        if not all_values:
            print("No data to plot")
            return
        
        vmin, vmax = min(all_values), max(all_values)
        
        for ax_idx, engine in enumerate(engines):
            ax = axes[ax_idx]
            
            matrix = np.full((len(worlds), len(horizons)), np.nan)
            for i, w in enumerate(worlds):
                for j, h in enumerate(horizons):
                    if w in organized[engine] and h in organized[engine][w]:
                        matrix[i, j] = organized[engine][w][h]["stats"][metric]
            
            im = ax.imshow(matrix, cmap='RdYlGn', aspect='auto',
                            vmin=vmin, vmax=vmax)
            
            ax.set_xticks(range(len(horizons)))
            ax.set_xticklabels([f"H{h}" for h in horizons])
            ax.set_yticks(range(len(worlds)))
            ax.set_yticklabels(worlds)
            
            ax.set_title(f"{engine}\n({metric})", fontsize=12, fontweight='bold')
            ax.set_xlabel("Horizon")
            
            # 値を表示
            for i in range(len(worlds)):
                for j in range(len(horizons)):
                    if not np.isnan(matrix[i, j]):
                        color = 'white' if matrix[i, j] < (vmin + vmax) / 2 else 'black'
                        ax.text(j, i, f"{matrix[i, j]:.2f}",
                                 ha='center', va='center',
                                 fontsize=9, color=color, fontweight='bold')
            
            plt.colorbar(im, ax=ax, label=metric)
        
        fig.suptitle(f"NRMO Benchmark — {metric.upper()} comparison",
                      fontsize=14, fontweight='bold')
        plt.tight_layout()
        plt.savefig(output_path, dpi=120, bbox_inches='tight',
                     facecolor='white')
        plt.close()
        print(f"Saved: {output_path}")
    
    def plot_pareto_check(self, output_path: str, baseline: str = "v7.1",
                          candidate: str = "v7.2"):
        """Pareto 改善検証プロット"""
        organized = self._organize()
        
        if baseline not in organized or candidate not in organized:
            print(f"Missing engine: {baseline} or {candidate}")
            return
        
        worlds = sorted(set(organized[baseline].keys()) & 
                        set(organized[candidate].keys()))
        all_horizons = set()
        for w in worlds:
            all_horizons.update(organized[baseline][w].keys())
            all_horizons.update(organized[candidate][w].keys())
        horizons = sorted(all_horizons)
        
        # Diff matrix (candidate - baseline)
        fig, axes = plt.subplots(1, 2, figsize=(16, 7), facecolor='white')
        
        for ax_idx, metric in enumerate(["median", "mean"]):
            ax = axes[ax_idx]
            diff_matrix = np.full((len(worlds), len(horizons)), np.nan)
            
            for i, w in enumerate(worlds):
                for j, h in enumerate(horizons):
                    if h in organized[baseline].get(w, {}) and \
                       h in organized[candidate].get(w, {}):
                        b = organized[baseline][w][h]["stats"][metric]
                        c = organized[candidate][w][h]["stats"][metric]
                        diff_matrix[i, j] = c - b
            
            # 改善は緑、悪化は赤
            max_abs = np.nanmax(np.abs(diff_matrix))
            im = ax.imshow(diff_matrix, cmap='RdYlGn', aspect='auto',
                            vmin=-max_abs, vmax=max_abs)
            
            ax.set_xticks(range(len(horizons)))
            ax.set_xticklabels([f"H{h}" for h in horizons])
            ax.set_yticks(range(len(worlds)))
            ax.set_yticklabels(worlds)
            
            ax.set_title(f"{candidate} - {baseline} ({metric})",
                          fontsize=12, fontweight='bold')
            ax.set_xlabel("Horizon")
            
            for i in range(len(worlds)):
                for j in range(len(horizons)):
                    if not np.isnan(diff_matrix[i, j]):
                        sign = "+" if diff_matrix[i, j] >= 0 else ""
                        ax.text(j, i, f"{sign}{diff_matrix[i, j]:.2f}",
                                 ha='center', va='center',
                                 fontsize=10, fontweight='bold',
                                 color='black')
            
            plt.colorbar(im, ax=ax, label="diff")
        
        fig.suptitle(f"Pareto 検証: {candidate} vs {baseline}",
                      fontsize=14, fontweight='bold')
        plt.tight_layout()
        plt.savefig(output_path, dpi=120, bbox_inches='tight',
                     facecolor='white')
        plt.close()
        print(f"Saved: {output_path}")
    
    def plot_distribution_comparison(self, output_path: str,
                                       baseline: str = "v7.1",
                                       candidate: str = "v7.2"):
        """Score 分布の重ね合わせ"""
        organized = self._organize()
        
        if baseline not in organized or candidate not in organized:
            return
        
        worlds = sorted(set(organized[baseline].keys()) & 
                        set(organized[candidate].keys()))
        all_horizons = set()
        for w in worlds:
            all_horizons.update(organized[baseline][w].keys())
        horizons = sorted(all_horizons)
        
        n_rows = len(worlds)
        n_cols = len(horizons)
        
        fig, axes = plt.subplots(n_rows, n_cols, 
                                  figsize=(4 * n_cols, 3 * n_rows),
                                  facecolor='white')
        if n_rows == 1:
            axes = [axes]
        if n_cols == 1:
            axes = [[a] for a in axes]
        
        for i, w in enumerate(worlds):
            for j, h in enumerate(horizons):
                ax = axes[i][j] if n_rows > 1 else axes[j]
                
                if h in organized[baseline].get(w, {}) and \
                   h in organized[candidate].get(w, {}):
                    b_scores = organized[baseline][w][h]["raw_scores"]
                    c_scores = organized[candidate][w][h]["raw_scores"]
                    
                    ax.hist(b_scores, bins=30, alpha=0.5, 
                            label=baseline, color='blue')
                    ax.hist(c_scores, bins=30, alpha=0.5,
                            label=candidate, color='orange')
                    
                    ax.axvline(np.median(b_scores), color='blue',
                                linestyle='--', linewidth=2)
                    ax.axvline(np.median(c_scores), color='orange',
                                linestyle='--', linewidth=2)
                    
                    ax.set_title(f"{w} H{h}", fontsize=10)
                    ax.legend(fontsize=8)
                    ax.set_xlabel("Score")
                    ax.set_ylabel("Count")
        
        fig.suptitle(f"Score 分布比較: {baseline} vs {candidate}",
                      fontsize=14, fontweight='bold')
        plt.tight_layout()
        plt.savefig(output_path, dpi=100, bbox_inches='tight',
                     facecolor='white')
        plt.close()
        print(f"Saved: {output_path}")
    
    def print_summary_table(self):
        """サマリーテーブルを print"""
        organized = self._organize()
        engines = sorted(organized.keys())
        
        print(f"\n{'='*80}")
        print("Benchmark Summary")
        print(f"{'='*80}\n")
        print(f"{'Engine':<8} {'World':<15} {'Horizon':<8} {'Median':<8} "
                f"{'Mean':<8} {'Std':<8} {'p25':<8} {'p75':<8}")
        print("-" * 80)
        
        for e in engines:
            for w in sorted(organized[e].keys()):
                for h in sorted(organized[e][w].keys()):
                    s = organized[e][w][h]["stats"]
                    print(f"{e:<8} {w:<15} {h:<8} {s['median']:<8.2f} "
                            f"{s['mean']:<8.2f} {s['std']:<8.2f} "
                            f"{s['p25']:<8.2f} {s['p75']:<8.2f}")


# ============================================================
# Main: 動作確認
# ============================================================

if __name__ == "__main__":
    # test_benchmark_results を可視化
    dashboard = BenchmarkDashboard("./test_benchmark_results")
    
    print(f"Loaded {len(dashboard.all_results)} cells")
    
    if dashboard.all_results:
        dashboard.print_summary_table()
        dashboard.plot_score_heatmap("./dashboard_heatmap.png")
        dashboard.plot_pareto_check("./dashboard_pareto.png")
        dashboard.plot_distribution_comparison("./dashboard_distribution.png")
    else:
        print("No results found. Run benchmark first.")
