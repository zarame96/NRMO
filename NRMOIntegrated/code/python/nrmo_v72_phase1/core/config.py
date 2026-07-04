"""
core/config.py

監査指摘 7 (ハードコード除去) への対応。
すべてのパスを config 経由で参照することで、絶対パス直書きを排除。
"""
from __future__ import annotations
import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, Optional


# プロジェクトルート (この config.py から見て 1 つ上が core/、2 つ上がプロジェクトルート)
_CORE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = _CORE_DIR.parent


@dataclass
class NRMOConfig:
    """NRMO 全体の設定"""
    project_root: Path = PROJECT_ROOT
    
    # ディレクトリ (project_root からの相対)
    core_dir: Path = field(init=False)
    phase7_dir: Path = field(init=False)
    phase8_dir: Path = field(init=False)
    phase9_dir: Path = field(init=False)
    phase10_dir: Path = field(init=False)
    phase11_dir: Path = field(init=False)
    validation_dir: Path = field(init=False)
    reports_dir: Path = field(init=False)
    results_dir: Path = field(init=False)
    
    # 実行パラメータ
    master_seed: int = 42
    n_workers: int = 4
    verbose: bool = True
    
    def __post_init__(self):
        self.core_dir = self.project_root / "core"
        self.phase7_dir = self.project_root / "phase7"
        self.phase8_dir = self.project_root / "phase8"
        self.phase9_dir = self.project_root / "phase9"
        self.phase10_dir = self.project_root / "phase10"
        self.phase11_dir = self.project_root / "phase11"
        self.validation_dir = self.project_root / "validation"
        self.reports_dir = self.project_root / "reports"
        self.results_dir = self.project_root / "results"
        
        # results / reports は実行時に作成可能
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.reports_dir.mkdir(parents=True, exist_ok=True)
    
    def output_dir(self, name: str) -> Path:
        """名前付き出力ディレクトリ"""
        d = self.results_dir / name
        d.mkdir(parents=True, exist_ok=True)
        return d
    
    @classmethod
    def from_env(cls, **overrides) -> "NRMOConfig":
        """環境変数から override"""
        params = {}
        if "NRMO_PROJECT_ROOT" in os.environ:
            params["project_root"] = Path(os.environ["NRMO_PROJECT_ROOT"])
        if "NRMO_SEED" in os.environ:
            params["master_seed"] = int(os.environ["NRMO_SEED"])
        if "NRMO_WORKERS" in os.environ:
            params["n_workers"] = int(os.environ["NRMO_WORKERS"])
        params.update(overrides)
        return cls(**params)


# シングルトン的なデフォルト config (環境変数 NRMO_PROJECT_ROOT で上書き可)
DEFAULT_CONFIG = NRMOConfig.from_env()


if __name__ == "__main__":
    cfg = NRMOConfig.from_env()
    print("NRMO Configuration:")
    print(f"  Project root: {cfg.project_root}")
    print(f"  Core dir:     {cfg.core_dir}")
    print(f"  Validation:   {cfg.validation_dir}")
    print(f"  Reports:      {cfg.reports_dir}")
    print(f"  Results:      {cfg.results_dir}")
    print(f"  Master seed:  {cfg.master_seed}")
    print(f"  Workers:      {cfg.n_workers}")
