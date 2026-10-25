#!/usr/bin/env python3
"""Validate and reproducibly package the all-employee NRMO Work Skill."""
import argparse
import hashlib
import io
import json
import re
import subprocess
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "skill" / "nrmo-work"
RELEASE_FILE = ROOT / "skill" / "work-release.json"
DESCRIPTION_LIMIT = 200
REQUIRED_PDF_SECTIONS = ("§60.3", "§63.1", "§63.2", "§64.1", "§64.2")
WORK_ONLY = {
    "references/WORKPLACE_BOUNDARIES.md",
    "references/RUNTIME_RECONCILIATION.md",
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def description(skill):
    match = re.match(r"\A---\nname: nrmo-work\ndescription: ([^\n]+)\n---\n", skill)
    if not match:
        raise ValueError("unexpected Work Skill frontmatter")
    if not 1 <= len(match.group(1)) <= DESCRIPTION_LIMIT:
        raise ValueError(
            f"Work Skill description must be 1-{DESCRIPTION_LIMIT} characters, "
            f"got {len(match.group(1))}"
        )
    return match.group(1)


def collect():
    release = json.loads(RELEASE_FILE.read_text(encoding="utf-8"))
    files = {}
    for path in sorted(SOURCE.rglob("*")):
        if path.is_symlink():
            raise ValueError(f"symlink is not allowed: {path}")
        if path.is_file():
            files[path.relative_to(SOURCE).as_posix()] = path.read_bytes()
    expected = set(release["reference_sha256"]) | {"SKILL.md"}
    if set(files) != expected:
        raise ValueError(f"unexpected/missing package files: {set(files) ^ expected}")
    for path, digest in release["reference_sha256"].items():
        if sha(files[path]) != digest:
            raise ValueError(f"reference hash mismatch: {path}")

    shared = set(release["reference_sha256"]) - WORK_ONLY
    for path in sorted(shared):
        personal = ROOT / "skill" / "nrmo" / path
        if files[path] != personal.read_bytes():
            raise ValueError(f"shared reference differs from approved personal rc12: {path}")

    canon_source = (ROOT / "NRMOIntegrated/NORMATIVE_CANON.md").read_text(
        encoding="utf-8"
    ).rstrip("\n")
    canon_copy = files["references/NORMATIVE_CANON.md"].decode("utf-8").rstrip("\n")
    if canon_copy != canon_source:
        raise ValueError("packaged Normative Canon differs from repository authority source")
    source_manifest = ROOT / "NRMOIntegrated/source/v7.3/original/SOURCE_MANIFEST.md"
    if files["references/SOURCE_MANIFEST.md"] != source_manifest.read_bytes():
        raise ValueError("packaged source manifest differs from immutable original")

    reconciliation = files["references/RUNTIME_RECONCILIATION.md"].decode("utf-8")
    if any(section not in reconciliation for section in REQUIRED_PDF_SECTIONS):
        raise ValueError("Work reconciliation is missing a mandatory PDF route")
    if '"463-474"' not in reconciliation or "211-216" not in reconciliation:
        raise ValueError("Work reconciliation is missing a required PDF range")
    if "Chapter 3 and Chapter 20" in reconciliation:
        raise ValueError("Work reconciliation routes epsilon to PDF Chapter 20")

    skill = files["SKILL.md"].decode("utf-8")
    description(skill)
    if release["version"] not in skill:
        raise ValueError("Work release version missing from Skill")
    required = (
        "WORKPLACE_BOUNDARIES.md",
        "本人の職務権限",
        "人事評価",
        "通報",
        "StrongEngine",
        "A_allowed",
        "ALB/NPMO",
    )
    if any(term not in skill for term in required):
        raise ValueError("Work Skill is missing a required employee boundary")
    if any(path.startswith("references/alb/") for path in files):
        raise ValueError("ALB research drafts must not ship in NRMO Work")
    if "references/ext_nonoverlap_v0_1.md" in files:
        raise ValueError("unadopted non-overlap draft must not ship in NRMO Work")
    return release, files, shared


def make_zip(files):
    buffer = io.BytesIO()
    with zipfile.ZipFile(
        buffer, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
    ) as archive:
        for path, data in sorted(files.items()):
            info = zipfile.ZipInfo(
                "nrmo-work/" + path, date_time=(1980, 1, 1, 0, 0, 0)
            )
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data, compresslevel=9)
    return buffer.getvalue()


def validate_archive(data, files):
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        expected = {"nrmo-work/" + path: content for path, content in files.items()}
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
    release, files, shared = collect()
    if args.output is None:
        args.output = ROOT / "dist" / "nrmo-work-rc1"

    package = make_zip(files)
    if package != make_zip(files):
        raise ValueError("package is not reproducible within this runtime")
    validate_archive(package, files)
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
    dirty = subprocess.check_output(
        [
            "git",
            "status",
            "--porcelain",
            "--",
            "skill/nrmo-work",
            "skill/work-release.json",
        ],
        cwd=ROOT,
        text=True,
    ).strip()
    if dirty:
        raise ValueError("Work package inputs differ from the recorded source commit")

    hashes = {path: sha(data) for path, data in sorted(files.items())}
    hash_list = "".join(
        f"{digest}  nrmo-work/{path}\n" for path, digest in hashes.items()
    )
    manifest = {
        "version": release["version"],
        "base_personal_version": release["base_personal_version"],
        "source_commit": commit,
        "status": release["status"],
        "package_sha256": sha(package),
        "tree_sha256": sha(hash_list.encode("utf-8")),
        "file_sha256": hashes,
        "checks": {
            "shared_references_byte_match_personal_rc12": len(shared),
            "archive_members": len(files),
            "round_trip": True,
            "same_runtime_reproducible": True,
            "mismatch_rejection": True,
            "description_characters": len(description(files["SKILL.md"].decode("utf-8"))),
            "description_limit": DESCRIPTION_LIMIT,
            "normative_canon_text_match": True,
            "source_manifest_byte_match": True,
            "alb_npmo_excluded": True,
            "nonoverlap_draft_excluded": True,
            "mandatory_pdf_routes": list(REQUIRED_PDF_SECTIONS),
        },
        "model_behavior": "NOT_RUN",
        "claude_ai_behavior": "NOT_RUN",
    }
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "nrmo-work.skill").write_bytes(package)
    (args.output / "BUILD_MANIFEST.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
