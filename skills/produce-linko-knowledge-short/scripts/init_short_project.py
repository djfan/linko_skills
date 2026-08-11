#!/usr/bin/env python3
"""Create a Linko knowledge Short project from bundled templates."""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path


TEMPLATES = {
    "short-brief.template.md": "short-brief.md",
    "project-state.template.json": "project-state.json",
    "research.template.md": "research.md",
    "script.template.md": "script.md",
    "shot-plan.template.json": "shot-plan.json",
    "asset-manifest.template.json": "asset-manifest.json",
    "voice-provenance.template.json": "audio/voice-provenance.json",
    "qa-report.template.md": "qa/qa-report.md",
    "publish-copy.template.md": "publish-copy.md",
    "release-checklist.template.md": "release-checklist.md",
}

DIRECTORIES = (
    "assets/source",
    "assets/linko",
    "assets/licensed",
    "audio",
    "render",
    "qa",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Initialize a clean Linko knowledge Short workspace."
    )
    parser.add_argument("project_directory", type=Path)
    parser.add_argument(
        "--force",
        action="store_true",
        help="Replace only generated template files that already exist.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    project = args.project_directory.expanduser().resolve()
    template_dir = Path(__file__).resolve().parent.parent / "assets"

    if project.exists() and not project.is_dir():
        print(f"error: project path is not a directory: {project}", file=sys.stderr)
        return 2

    project.mkdir(parents=True, exist_ok=True)
    for relative in DIRECTORIES:
        (project / relative).mkdir(parents=True, exist_ok=True)

    created: list[str] = []
    skipped: list[str] = []
    for source_name, destination_name in TEMPLATES.items():
        source = template_dir / source_name
        destination = project / destination_name
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists() and not args.force:
            skipped.append(destination_name)
            continue
        shutil.copyfile(source, destination)
        created.append(destination_name)

    print(f"project: {project}")
    print("created: " + (", ".join(created) if created else "none"))
    print("skipped: " + (", ".join(skipped) if skipped else "none"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
