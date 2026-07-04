"""
NRMO v7.2 Phase 1 — Benchmark Runner & Checkpoint

シミュレーション自動実行とチェックポイント機構:
  - 100K runs を 5 worlds × 5 horizons で実行
  - 結果を JSON / parquet で永続化
  - 中断時の再開対応
  - 並列実行サポート
"""
import json
import os
import sys
import pickle
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from concurrent.futures import ProcessPoolExecutor, as_completed
import numpy as np

# パス設定
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))

from world_models import World, WorldType, WorldState, Action
from engines import V50Engine, V71Engine, V72Engine


# ============================================================
# 設定
# ============================================================

@dataclass
class BenchmarkConfig:
    """ベンチマーク設定"""
    engines: List[str] = field(default_factory=lambda: ["v5.0", "v7.1", "v7.2"])
    worlds: List[str] = field(default_factory=lambda: [
        "Normal", "FastExpansion", "Vulnerable", "Stagnation", "Race"
    ])
    horizons: List[int] = field(default_factory=lambda: [200, 500, 1000])
    runs_per_cell: int = 1000  # Phase 1 quick 用に小さめ
    n_workers: int = 4
    checkpoint_dir: str = "./benchmark_results"
    seed_base: int = 0


# ============================================================
# 単一 run の実行
# ============================================================

def run_single(args: Tuple) -> Dict:
    """1 run の実行 (並列化用、グローバル関数)"""
    engine_name, world_name, horizon, seed = args
    
    # エンジンインスタンス化
    if engine_name == "v5.0":
        engine = V50Engine()
    elif engine_name == "v7.1":
        engine = V71Engine()
    elif engine_name == "v7.2":
        engine = V72Engine()
    else:
        raise ValueError(f"Unknown engine: {engine_name}")
    
    # World 初期化
    world_type = WorldType[world_name.upper().replace("EXPANSION", "_EXPANSION")] \
        if "Expansion" in world_name else WorldType[world_name.upper()]
    world = World(world_type, seed=seed)
    
    # シミュレーション
    for t in range(horizon):
        action = engine.select_action(world.state)
        state, reward, done, info = world.step(action)
        if hasattr(engine, 'update_reward'):
            engine.update_reward(action, reward)
        if done:
            break
    
    # 結果取得
    result = {
        "engine": engine_name,
        "world": world_name,
        "horizon": horizon,
        "seed": seed,
        "final_score": world.state.cumulative_score,
        "final_t": world.state.t,
        "is_ruined": world.state.is_ruined,
        "final_R": world.state.R,
        "final_E": world.state.E,
        "final_G": world.state.G,
        "final_X": world.state.X,
        "final_O": world.state.O,
    }
    
    # v7.2 のメトリクスも記録
    if engine_name == "v7.2" and hasattr(engine, 'get_metrics'):
        metrics = engine.get_metrics()
        result["v72_metrics"] = metrics
    
    return result


# ============================================================
# Cell の実行 (engine × world × horizon)
# ============================================================

def run_cell(engine_name: str, world_name: str, horizon: int, 
             n_runs: int, n_workers: int = 4, seed_base: int = 0) -> Dict:
    """1 cell (engine × world × horizon) の全 runs 実行"""
    print(f"  [{engine_name}] {world_name} H={horizon}: n_runs={n_runs}", flush=True)
    
    args_list = [
        (engine_name, world_name, horizon, seed_base + i)
        for i in range(n_runs)
    ]
    
    start = time.time()
    results = []
    
    # 並列実行
    with ProcessPoolExecutor(max_workers=n_workers) as executor:
        for i, result in enumerate(executor.map(run_single, args_list)):
            results.append(result)
            if (i + 1) % max(1, n_runs // 10) == 0:
                elapsed = time.time() - start
                rate = (i + 1) / elapsed
                eta = (n_runs - i - 1) / rate
                print(f"    {i+1}/{n_runs} [{rate:.0f} runs/sec, ETA {eta:.0f}s]",
                      flush=True)
    
    elapsed = time.time() - start
    
    # 統計を計算
    scores = np.array([r["final_score"] for r in results])
    ruin_rate = np.mean([r["is_ruined"] for r in results])
    
    cell_summary = {
        "cell_id": f"{engine_name}_{world_name}_H{horizon}",
        "engine": engine_name,
        "world": world_name,
        "horizon": horizon,
        "n_runs": n_runs,
        "elapsed_sec": elapsed,
        "stats": {
            "mean": float(np.mean(scores)),
            "median": float(np.median(scores)),
            "std": float(np.std(scores)),
            "min": float(np.min(scores)),
            "max": float(np.max(scores)),
            "p10": float(np.percentile(scores, 10)),
            "p25": float(np.percentile(scores, 25)),
            "p75": float(np.percentile(scores, 75)),
            "p90": float(np.percentile(scores, 90)),
            "ruin_rate": float(ruin_rate),
        },
        "raw_scores": scores.tolist(),  # 統計検定用
    }
    
    return cell_summary


# ============================================================
# チェックポイント機構
# ============================================================

class CheckpointManager:
    """結果の永続化と中断・再開対応"""
    
    def __init__(self, checkpoint_dir: str):
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self.completed_cells = self._load_completed()
    
    def _load_completed(self) -> set:
        """既に完了した cell ID を取得"""
        completed = set()
        for f in self.checkpoint_dir.glob("*.json"):
            completed.add(f.stem)
        return completed
    
    def is_completed(self, cell_id: str) -> bool:
        return cell_id in self.completed_cells
    
    def save_cell(self, cell_summary: Dict):
        """cell 結果を保存"""
        cell_id = cell_summary["cell_id"]
        path = self.checkpoint_dir / f"{cell_id}.json"
        with open(path, "w") as f:
            json.dump(cell_summary, f, indent=2)
        self.completed_cells.add(cell_id)
    
    def load_cell(self, cell_id: str) -> Optional[Dict]:
        path = self.checkpoint_dir / f"{cell_id}.json"
        if not path.exists():
            return None
        with open(path, "r") as f:
            return json.load(f)
    
    def load_all(self) -> List[Dict]:
        all_results = []
        for f in self.checkpoint_dir.glob("*.json"):
            with open(f, "r") as g:
                all_results.append(json.load(g))
        return all_results
    
    def status(self) -> Dict:
        return {
            "completed": len(self.completed_cells),
            "completed_ids": sorted(self.completed_cells),
        }


# ============================================================
# メイン Benchmark Runner
# ============================================================

class BenchmarkRunner:
    """ベンチマーク全体の制御"""
    
    def __init__(self, config: BenchmarkConfig):
        self.config = config
        self.checkpoint = CheckpointManager(config.checkpoint_dir)
    
    def run_all(self, skip_completed: bool = True):
        """設定されたすべての cell を実行"""
        cells = []
        for engine in self.config.engines:
            for world in self.config.worlds:
                for horizon in self.config.horizons:
                    cell_id = f"{engine}_{world}_H{horizon}"
                    cells.append((cell_id, engine, world, horizon))
        
        print(f"Total cells to run: {len(cells)}")
        print(f"Already completed: {len(self.checkpoint.completed_cells)}")
        
        start = time.time()
        for i, (cell_id, engine, world, horizon) in enumerate(cells):
            if skip_completed and self.checkpoint.is_completed(cell_id):
                print(f"[{i+1}/{len(cells)}] {cell_id}: SKIP (completed)")
                continue
            
            print(f"\n[{i+1}/{len(cells)}] {cell_id}")
            cell_summary = run_cell(
                engine_name=engine,
                world_name=world,
                horizon=horizon,
                n_runs=self.config.runs_per_cell,
                n_workers=self.config.n_workers,
                seed_base=self.config.seed_base,
            )
            self.checkpoint.save_cell(cell_summary)
        
        total_elapsed = time.time() - start
        print(f"\n{'='*60}")
        print(f"Benchmark complete in {total_elapsed:.1f}s")
        print(f"Results saved to: {self.config.checkpoint_dir}")
    
    def summarize(self) -> Dict:
        """全結果のサマリー"""
        all_results = self.checkpoint.load_all()
        
        # engine × world × horizon でグループ化
        summary = {}
        for r in all_results:
            engine = r["engine"]
            world = r["world"]
            horizon = r["horizon"]
            
            if engine not in summary:
                summary[engine] = {}
            if world not in summary[engine]:
                summary[engine][world] = {}
            summary[engine][world][f"H{horizon}"] = r["stats"]
        
        return summary


# ============================================================
# 動作確認 (quick test)
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("NRMO v7.2 Phase 1 — Benchmark Runner 動作確認")
    print("=" * 60)
    
    # 小規模クイックテスト
    config = BenchmarkConfig(
        engines=["v5.0", "v7.1", "v7.2"],
        worlds=["Normal", "Vulnerable"],
        horizons=[200],
        runs_per_cell=100,
        n_workers=4,
        checkpoint_dir="./test_benchmark_results",
    )
    
    runner = BenchmarkRunner(config)
    runner.run_all()
    
    print("\n" + "=" * 60)
    print("サマリー")
    print("=" * 60)
    summary = runner.summarize()
    for engine, worlds in summary.items():
        for world, horizons in worlds.items():
            for h_key, stats in horizons.items():
                print(f"  {engine} | {world} | {h_key}: "
                      f"mean={stats['mean']:6.2f} "
                      f"median={stats['median']:6.2f} "
                      f"std={stats['std']:5.2f} "
                      f"ruin={stats['ruin_rate']:.0%}")
