"""
NRMO v7.2 Phase 3 — Optimization Visualization
"""
import os
import sys
import json
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

try:
    fm.fontManager.addfont('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc')
    plt.rcParams['font.family'] = 'Noto Sans CJK JP'
except Exception:
    pass
plt.rcParams['axes.unicode_minus'] = False

NAVY = '#1A2848'
GREEN = '#2ECC71'
RED = '#E74C3C'
BLUE = '#4A90E2'
ORANGE = '#F0AD4E'


def plot_optimization_history(history_path: str, output_path: str):
    """最適化の履歴をプロット"""
    with open(history_path) as f:
        history = json.load(f)
    
    if not history:
        return
    
    steps = [h["step"] for h in history]
    composite = [h["composite_score"] for h in history]
    n_active = [h["n_active"] for h in history]
    violations = [h["pareto_violations"] for h in history]
    improvement = [h["total_improvement"] for h in history]
    
    fig, axes = plt.subplots(2, 2, figsize=(14, 10), facecolor='white')
    
    # Composite Score
    ax = axes[0, 0]
    ax.plot(steps, composite, marker='o', linewidth=2, color=NAVY)
    ax.fill_between(steps, composite, alpha=0.2, color=NAVY)
    ax.set_xlabel("Step")
    ax.set_ylabel("Composite Score")
    ax.set_title("Composite Score progression",
                  fontsize=12, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.axhline(y=0, color='black', linewidth=0.5)
    
    # Best so far
    best_so_far = np.maximum.accumulate(composite)
    ax.plot(steps, best_so_far, '--', color=GREEN, linewidth=2,
             label='Best so far')
    ax.legend()
    
    # Active features count
    ax = axes[0, 1]
    ax.plot(steps, n_active, marker='s', linewidth=2, color=BLUE)
    ax.set_xlabel("Step")
    ax.set_ylabel("Active features count")
    ax.set_title("# of active features",
                  fontsize=12, fontweight='bold')
    ax.set_ylim(0, 22)
    ax.grid(True, alpha=0.3)
    ax.axhline(y=22, color=RED, linestyle=':', alpha=0.5, label='All ON')
    ax.axhline(y=0, color=BLUE, linestyle=':', alpha=0.5, label='All OFF')
    ax.legend()
    
    # Pareto violations
    ax = axes[1, 0]
    ax.bar(steps, violations, color=[RED if v > 0 else GREEN for v in violations])
    ax.set_xlabel("Step")
    ax.set_ylabel("Pareto violations")
    ax.set_title("Pareto violations (lower is better)",
                  fontsize=12, fontweight='bold')
    ax.grid(True, alpha=0.3)
    
    # Total improvement
    ax = axes[1, 1]
    colors = [GREEN if v > 0 else RED for v in improvement]
    ax.bar(steps, improvement, color=colors)
    ax.set_xlabel("Step")
    ax.set_ylabel("Total improvement")
    ax.set_title("Total improvement (vs v7.1)",
                  fontsize=12, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.axhline(y=0, color='black', linewidth=0.5)
    
    fig.suptitle("Phase 3 Optimization History",
                  fontsize=14, fontweight='bold', y=1.00)
    plt.tight_layout()
    plt.savefig(output_path, dpi=120, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f"Saved: {output_path}")


def plot_final_selection(result_path: str, output_path: str):
    """最終選定機能の可視化"""
    with open(result_path) as f:
        result = json.load(f)
    
    all_features = (
        ["I8", "I9", "I10", "I11", "I12"] +
        ["H1", "H2", "H3", "H4", "H5", "H6", "H7"] +
        ["G1", "G2", "G3", "G4", "G5", "G6", "G7", "G8", "G9", "G10"]
    )
    
    active = set(result["best_active_features"])
    
    fig, ax = plt.subplots(figsize=(14, 8), facecolor='white')
    
    # 機能をカテゴリ別にプロット
    categories = {
        "Invariants": ["I8", "I9", "I10", "I11", "I12"],
        "HOLD": ["H1", "H2", "H3", "H4", "H5", "H6", "H7"],
        "Gates": ["G1", "G2", "G3", "G4", "G5", "G6", "G7", "G8", "G9", "G10"],
    }
    
    y = 0
    yticks = []
    yticklabels = []
    for cat, features in categories.items():
        for f in features:
            color = GREEN if f in active else '#DDDDDD'
            edge = NAVY if f in active else '#999999'
            ax.barh(y, 1, color=color, edgecolor=edge, linewidth=1.5)
            label = f"{f} ✓" if f in active else f"{f}"
            ax.text(0.5, y, label, ha='center', va='center',
                     fontsize=10, fontweight='bold' if f in active else 'normal',
                     color='black')
            yticks.append(y)
            yticklabels.append("")
            y += 1
        # カテゴリ区切り
        ax.axhline(y - 0.5, color='black', linewidth=2)
        y += 0.5
    
    # カテゴリラベル (左側)
    cat_y = 2.0
    for cat in categories:
        ax.text(-0.05, cat_y, cat, ha='right', va='center',
                 fontsize=12, fontweight='bold', rotation=0,
                 color=NAVY)
        cat_y += len(categories[cat]) + 0.5
    
    ax.set_xlim(-0.5, 1.2)
    ax.set_ylim(-0.5, y + 0.5)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['bottom'].set_visible(False)
    ax.spines['left'].set_visible(False)
    
    # 結果サマリーをタイトルに
    ax.set_title(
        f"Optimized v7.2 Feature Subset: {result['n_active']}/22 features\n"
        f"Composite: {result['composite_score']:+.3f} | "
        f"Improvements: {result.get('strict_improvements', 0)} | "
        f"Violations: {result['pareto_violations']}",
        fontsize=14, fontweight='bold', pad=20,
    )
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=120, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f"Saved: {output_path}")


if __name__ == "__main__":
    output_dir = "./optimization_analysis"
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    plot_optimization_history(
        "./optimization_history.json",
        f"{output_dir}/history.png",
    )
    
    plot_final_selection(
        "./optimization_result.json",
        f"{output_dir}/final_selection.png",
    )
