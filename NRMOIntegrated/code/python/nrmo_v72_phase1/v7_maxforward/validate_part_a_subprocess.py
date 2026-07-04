"""
validate_part_a_subprocess.py — Part A 専用 (subprocess 分離)。
本物サブシステム (Omega/Wolf/Shinobi/MAPLayer/Norn-Skuld/Loom) が発火するかだけを見る。
- 軽量・短時間
- "ALL SUBSYSTEMS ALIVE" を出す
- 破滅有無は本テストの合否にしない
- 終了コード 0/1
Part B とは別プロセスで実行され、状態を持ち越さない。
"""
from __future__ import annotations
import os, sys
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.join(_HERE, "..", "core"))

import omega_full_integrated as ofi

def main():
    checks, _u, _s, _l = ofi.validate_subsystems_alive()
    print("[PART A] 本物サブシステム生存 (Wolf/Shinobi/MAPLayer/Norn-Skuld/Loom)")
    n_fail = 0
    for name, ok in checks:
        print(f"  {'PASS' if ok else 'FAIL'}: {name}")
        if not ok:
            n_fail += 1
    print("-" * 50)
    if n_fail == 0:
        print("ALL SUBSYSTEMS ALIVE")
        sys.exit(0)
    print(f"SOME SUBSYSTEM HOLLOW/INACTIVE ({n_fail})")
    sys.exit(1)

if __name__ == "__main__":
    main()
