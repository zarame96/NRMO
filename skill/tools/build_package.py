#!/usr/bin/env python3
"""Validate and reproducibly package the personal Skill; never grades model behavior."""
import argparse
import hashlib
import io
import json
import re
import subprocess
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "skill" / "nrmo"
DESCRIPTION_LIMIT = 200


def sha(data):
    return hashlib.sha256(data).hexdigest()


def description(skill):
    match = re.match(r"\A---\nname: nrmo\ndescription: ([^\n]+)\n---\n", skill)
    if not match:
        raise ValueError("unexpected Skill frontmatter")
    # claude.ai's documented limit; the rc8 description (235 chars) exceeded it.
    if not 1 <= len(match.group(1)) <= DESCRIPTION_LIMIT:
        raise ValueError(f"Skill description must be 1-{DESCRIPTION_LIMIT} characters, got {len(match.group(1))}")
    return match.group(1)


def collect():
    release = json.loads((ROOT / "skill/release.json").read_text(encoding="utf-8"))
    files = {}
    for path in sorted(SOURCE.rglob("*")):
        if path.is_symlink():
            raise ValueError(f"symlink is not allowed: {path}")
        if path.is_file():
            files[path.relative_to(SOURCE).as_posix()] = path.read_bytes()
    expected = set(release["reference_sha256"]) | {"SKILL.md", "references/PDF_CAVEATS.md"}
    if set(files) != expected:
        raise ValueError(f"unexpected/missing package files: {set(files) ^ expected}")
    for path, digest in release["reference_sha256"].items():
        if sha(files[path]) != digest:
            raise ValueError(f"unchanged-reference hash mismatch: {path}")
    skill = files["SKILL.md"].decode("utf-8")
    description(skill)
    if release["version"] not in skill:
        raise ValueError("release version missing from Skill")
    if any(term in skill for term in ("NRMOなしで", "外部判定として", "NRMOを使わずに")):
        raise ValueError("removed dedicated opt-out rule remains in current Skill")
    for ref in re.findall(r"`(references/[^ `]+)`", skill):
        if ref.endswith("/"):
            if not any(path.startswith(ref) for path in files):
                raise ValueError(f"missing referenced directory: {ref}")
        elif ref not in files:
            raise ValueError(f"missing Skill reference: {ref}")
    return release, files


def make_zip(files):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path, data in sorted(files.items()):
            info = zipfile.ZipInfo("nrmo/" + path, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data, compresslevel=9)
    return buffer.getvalue()


def validate_archive(data, files):
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        expected = {"nrmo/" + path: content for path, content in files.items()}
        if len(archive.infolist()) != len(expected) or set(archive.namelist()) != set(expected):
            raise ValueError("archive has missing, extra, or duplicate members")
        if archive.testzip() is not None:
            raise ValueError("archive CRC validation failed")
        for path, content in expected.items():
            if archive.read(path) != content:
                raise ValueError(f"archive/source mismatch: {path}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    release, files = collect()
    if args.output is None:
        args.output = ROOT / "dist" / ("nrmo-" + release["version"].rsplit("-", 1)[-1])
    package = make_zip(files)
    if package != make_zip(files):
        raise ValueError("package is not reproducible within this runtime")
    validate_archive(package, files)
    # A corrupt package must not pass the same verifier.
    damaged = dict(files)
    damaged["SKILL.md"] = files["SKILL.md"] + b"\nchanged"
    try:
        validate_archive(package, damaged)
    except ValueError:
        pass
    else:
        raise AssertionError("archive/source mismatch was not detected")
    commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()
    if subprocess.check_output(["git", "status", "--porcelain", "--", "skill/nrmo", "skill/release.json"],
                               cwd=ROOT, text=True).strip():
        raise ValueError("package inputs differ from the recorded source commit")
    hashes = {path: sha(data) for path, data in sorted(files.items())}
    hash_list = "".join(f"{digest}  nrmo/{path}\n" for path, digest in hashes.items())
    manifest = {
        "version": release["version"],
        "source_commit": commit,
        "status": release["status"],
        "package_sha256": sha(package),
        "tree_sha256": sha(hash_list.encode("utf-8")),
        "file_sha256": hashes,
        "checks": {
            "unchanged_references": len(release["reference_sha256"]),
            "archive_members": len(files),
            "round_trip": True,
            "same_runtime_reproducible": True,
            "mismatch_rejection": True,
            "description_characters": len(description(files["SKILL.md"].decode("utf-8"))),
            "description_limit": DESCRIPTION_LIMIT,
        },
        "model_behavior": "NOT_RUN",
        "claude_ai_behavior": "NOT_RUN",
    }
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "nrmo.skill").write_bytes(package)
    (args.output / "BUILD_MANIFEST.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
