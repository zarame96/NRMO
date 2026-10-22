#!/usr/bin/env python3
"""Build the rc8 claude.ai upload variant; do not alter the tested rc8 source."""
import argparse
import hashlib
import io
import json
import re
import zipfile
from pathlib import Path

from build_package import make_zip, validate_archive

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "skill/archive/v1.0.0-rc8/nrmo.skill"
BASE_SHA256 = "f6b90797f696044a32aecf05a400db5c468c2a8cb0e4fdb34e0518f1faa5d9c4"
DESCRIPTION = (
    "NRMO v7.3の意思決定支援。判断・比較・迷い・撤退・投資・仕事・人間関係の相談では毎回使う。"
    "/nrmo、NRMO、Norn、StrongEngine、Type ZERO、A_allowed、破綻境界、HOLD、"
    "非重複拡張の理論・設計・レビューにも使う。ALBは研究草稿の理論質問のみ対象。"
)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def build():
    original = BASE.read_bytes()
    if sha(original) != BASE_SHA256:
        raise ValueError("rc8 base archive does not match the fixed package")
    with zipfile.ZipFile(io.BytesIO(original)) as archive:
        if archive.testzip() is not None:
            raise ValueError("base archive CRC failure")
        names = archive.namelist()
        if len(names) != 19 or len(set(names)) != len(names):
            raise ValueError("unexpected rc8 member count")
        if any(not name.startswith("nrmo/") or ".." in Path(name).parts for name in names):
            raise ValueError("unexpected rc8 member path")
        files = {name.removeprefix("nrmo/"): archive.read(name) for name in names}
    before = files["SKILL.md"].decode("utf-8")
    match = re.match(r"\A---\nname: nrmo\ndescription: ([^\n]+)\n---\n", before)
    if not match or not 1 <= len(DESCRIPTION) <= 200:
        raise ValueError("invalid source metadata or upload description length")
    after = before[:match.start(1)] + DESCRIPTION + before[match.end(1):]
    if after.split("\n---\n", 1)[1] != before.split("\n---\n", 1)[1]:
        raise ValueError("Skill body changed")
    files["SKILL.md"] = after.encode("utf-8")
    package = make_zip(files)
    validate_archive(package, files)
    if package != make_zip(files):
        raise ValueError("upload package is not reproducible")
    manifest = {
        "variant": "v1.0.0-rc8-upload1",
        "base_source_commit": "e168af2acdce4f5f8a045a7740b61a197b519ced",
        "base_package_sha256": BASE_SHA256,
        "package_sha256": sha(package),
        "changed_field": "SKILL.md YAML description only",
        "description_characters_before": len(match.group(1)),
        "description_characters_after": len(DESCRIPTION),
        "description_limit_for_claude_ai": 200,
        "skill_body_unchanged": True,
        "unchanged_reference_files": 18,
        "file_sha256": {name: sha(data) for name, data in sorted(files.items())},
        "claude_ai_upload": "NOT_RUN",
        "variant_model_behavior": "NOT_RUN",
    }
    return package, manifest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "dist/nrmo-rc8-upload1")
    args = parser.parse_args()
    package, manifest = build()
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "nrmo.skill").write_bytes(package)
    (args.output / "BUILD_MANIFEST.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
