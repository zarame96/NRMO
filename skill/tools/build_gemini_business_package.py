#!/usr/bin/env python3
"""Build a deterministic Gemini Gem transfer package for NRMO Business."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import tempfile
import zipfile
from pathlib import Path


FIXED_ZIP_TIME = (1980, 1, 1, 0, 0, 0)
PACKAGE_NAME = "nrmo-business-gemini-rc1.zip"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def strip_frontmatter(text: str) -> str:
    if not text.startswith("---\n"):
        return text
    end = text.find("\n---\n", 4)
    if end < 0:
        raise ValueError("SKILL.md frontmatter is not closed")
    return text[end + 5 :]


def build_instructions(skill_path: Path) -> str:
    body = strip_frontmatter(skill_path.read_text(encoding="utf-8")).strip()
    body = re.sub(
        r"references/([A-Za-z0-9_./-]+)",
        lambda match: (
            "NRMO_Integrated_System_v7_3.pdf"
            if match.group(1) == "NRMO_Integrated_System_v7_3.pdf"
            else f"NRMO_BUSINESS_KNOWLEDGE.md 内の SOURCE: {match.group(1)}"
        ),
        body,
    )
    preface = """NRMO Business 管理者版として動作する。

以下の規則を最優先のカスタム指示として守る。Knowledge に登録された
NRMO_BUSINESS_KNOWLEDGE.md と NRMO_Integrated_System_v7_3.pdf を根拠として使う。
Knowledge を参照できない場合は、参照できない範囲と回答の限界を明示し、
記憶や一般論で正典を補完しない。AI自身は承認者・実行者・監査者にならない。

"""
    return preface + body + "\n"


def build_knowledge(reference_root: Path) -> str:
    parts = [
        "# NRMO Business Gemini Knowledge\n",
        "この文書は管理者版のテキスト参照資料を一つに統合したもの。各節の見出しは元ファイル名を示す。PDF本文は別ファイルを正本として参照する。\n",
    ]
    text_files = sorted(
        path for path in reference_root.rglob("*")
        if path.is_file() and path.suffix.lower() != ".pdf"
    )
    for path in text_files:
        rel = path.relative_to(reference_root).as_posix()
        parts.append(f"\n---\n\n# SOURCE: {rel}\n\n")
        parts.append(path.read_text(encoding="utf-8").rstrip())
        parts.append("\n")
    return "".join(parts)


def write_zip(zip_path: Path, members: list[Path], root: Path) -> None:
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(members, key=lambda item: item.name):
            info = zipfile.ZipInfo(path.name, FIXED_ZIP_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, path.read_bytes())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--source-commit", required=True)
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    source_root = repo_root / "skill" / "nrmo-business"
    reference_root = source_root / "references"
    pdf_source = reference_root / "NRMO_Integrated_System_v7_3.pdf"
    skill_source = source_root / "SKILL.md"

    if not skill_source.is_file() or not pdf_source.is_file():
        raise SystemExit("nrmo-business source or canonical PDF is missing")

    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    zip_path = output_dir / PACKAGE_NAME

    with tempfile.TemporaryDirectory() as temp_name:
        stage = Path(temp_name)
        (stage / "GEM_INSTRUCTIONS.txt").write_text(
            build_instructions(skill_source), encoding="utf-8", newline="\n"
        )
        (stage / "NRMO_BUSINESS_KNOWLEDGE.md").write_text(
            build_knowledge(reference_root), encoding="utf-8", newline="\n"
        )
        shutil.copyfile(pdf_source, stage / pdf_source.name)
        (stage / "INSTALL.txt").write_text(
            """NRMO Business Gemini rc1 導入手順

1. Gemini Web (gemini.google.com) で Gems → New Gem を開く。
2. 名前を「NRMO Business」にする。
3. GEM_INSTRUCTIONS.txt の全文を Instructions に貼り付ける。
4. Knowledge に次の2ファイルを個別に追加する。
   - NRMO_BUSINESS_KNOWLEDGE.md
   - NRMO_Integrated_System_v7_3.pdf
5. Previewでテストし、問題がなければSaveする。

ZIP自体やINSTALL.txt、KNOWLEDGE_SHA256SUMS.txtはKnowledgeへ追加しない。
ALB/NPMOは未採用であり、通常判定に使わない。
この候補版はモデル実動作試験・Gem実機試験が未実施で、正式承認前である。
""",
            encoding="utf-8",
            newline="\n",
        )
        checks = []
        for name in [
            "GEM_INSTRUCTIONS.txt",
            "NRMO_BUSINESS_KNOWLEDGE.md",
            "NRMO_Integrated_System_v7_3.pdf",
        ]:
            checks.append(f"{sha256(stage / name)}  {name}")
        (stage / "KNOWLEDGE_SHA256SUMS.txt").write_text(
            "\n".join(checks) + "\n", encoding="utf-8", newline="\n"
        )
        members = [
            stage / "GEM_INSTRUCTIONS.txt",
            stage / "INSTALL.txt",
            stage / "KNOWLEDGE_SHA256SUMS.txt",
            stage / "NRMO_BUSINESS_KNOWLEDGE.md",
            stage / "NRMO_Integrated_System_v7_3.pdf",
        ]
        write_zip(zip_path, members, stage)

        member_records = [
            {"name": path.name, "sha256": sha256(path), "size": path.stat().st_size}
            for path in sorted(members, key=lambda item: item.name)
        ]

    manifest = {
        "format": "nrmo-business-gemini-package-v1",
        "version": "v1.0.0-business-gemini-rc1",
        "source_commit": args.source_commit,
        "package": PACKAGE_NAME,
        "package_sha256": sha256(zip_path),
        "members": member_records,
    }
    (output_dir / "BUILD_MANIFEST.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
