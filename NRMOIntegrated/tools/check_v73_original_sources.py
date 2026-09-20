#!/usr/bin/env python3
"""check_v73_original_sources.py — byte-integrity guard for the located
NRMO v7.3 original source files.

Prevents the exact incident this tool is a response to: a "source
package supplied" (per DecisionCompass Issue #120) referenced by this
repository's provenance documents while the referenced files themselves
were absent from the repository.

Checks, in order:
1. SOURCE_MANIFEST.md exists.
2. Both original files listed in the manifest exist on disk, at the
   exact filenames the manifest records.
3. Each file's SHA-256 matches the value recorded in the manifest.

This is a byte-integrity guard, not a content/semantic guard: it does
not parse, validate, or apply any regex against the original files'
text. The two original files are immutable per
NRMOIntegrated/source/v7.3/original/SOURCE_MANIFEST.md's own policy;
this tool only verifies that immutability holds, and that both files
and the manifest remain where provenance documents (Part XVI,
V7_3_DIFFERENTIAL_TABLE.md, V7_3_ORIGINAL_SOURCE_DISCOVERY_RECORD.md)
say they are.

Exit 0 = all checks pass. Exit 1 = a check failed.
"""
import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE_DIR = ROOT / "source" / "v7.3" / "original"
MANIFEST = SOURCE_DIR / "SOURCE_MANIFEST.md"

EXPECTED = {
    "NRMO SYSTEM_7.3.md": (
        "474b635063830d12ec4065e6a13d77ab455af4bfef70e10e917a07948e85c712"
    ),
    "NRMO_SYSTEM_v7_3_PATCH.md": (
        "dbb79f8aeb4455031f598da7666608374fc7cbfcd0c8220629972b4b1705825d"
    ),
}


def fail(msg):
    print(f"  FAIL: {msg}")


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def main():
    failures = []

    if not MANIFEST.exists():
        failures.append(f"SOURCE_MANIFEST.md not found at {MANIFEST}")
    else:
        manifest_text = MANIFEST.read_text(encoding="utf-8")
        for filename, expected_hash in EXPECTED.items():
            if expected_hash not in manifest_text:
                failures.append(
                    f"expected SHA-256 for {filename!r} not found in "
                    f"SOURCE_MANIFEST.md (manifest may be out of sync "
                    f"with this guard's hardcoded expectations)"
                )

    for filename, expected_hash in EXPECTED.items():
        path = SOURCE_DIR / filename
        if not path.exists():
            failures.append(f"original file missing: {path}")
            continue
        actual_hash = sha256_of(path)
        if actual_hash != expected_hash:
            failures.append(
                f"{filename}: SHA-256 mismatch — expected {expected_hash}, "
                f"got {actual_hash} (file may have been edited; the "
                f"immutable-original policy in SOURCE_MANIFEST.md "
                f"prohibits this)"
            )

    print("[V7.3 ORIGINAL-SOURCE INTEGRITY GUARD]")
    if failures:
        for f in failures:
            fail(f)
        print(f"FOUND {len(failures)} integrity violation(s)")
        return 1
    print(
        "OK: SOURCE_MANIFEST.md present; both original files present and "
        "byte-identical to their recorded SHA-256"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
