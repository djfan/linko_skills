#!/usr/bin/env python3
"""Validate a Linko knowledge Short project contract and release gates."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


REQUIRED_FILES = (
    "short-brief.md",
    "project-state.json",
    "research.md",
    "script.md",
    "shot-plan.json",
    "asset-manifest.json",
    "publish-copy.md",
    "release-checklist.md",
    "qa/qa-report.md",
)

STATUSES = {"draft", "blocked", "review-ready", "publish-approved", "published"}
STAGES = {
    "preflight",
    "source-research",
    "angle-approval",
    "script-and-shot-plan",
    "rights-and-privacy",
    "linko-capture",
    "voice-and-edit",
    "automated-qa",
    "phone-qa",
    "publication-approval",
    "published",
}
APPROVED_RIGHTS = {"owned", "licensed", "public-domain", "authorized", "human-approved"}
APPROVED_PRIVACY = {"approved", "not-applicable"}
PUBLIC_CTA_PHRASES = ("follow me on linko", "follow my notes on linko", "full notes in linko")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project_directory", type=Path)
    parser.add_argument(
        "--release-ready",
        action="store_true",
        help="Require every final publication gate to pass.",
    )
    parser.add_argument("--report", type=Path, help="Write the JSON result to this path.")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"cannot read {path.name}: {error}") from error
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} must contain a JSON object")
    return value


def add_check(
    checks: list[dict[str, Any]], name: str, passed: bool, actual: Any, expected: str
) -> None:
    checks.append(
        {"name": name, "passed": passed, "actual": actual, "expected": expected}
    )


def main() -> int:
    args = parse_args()
    project = args.project_directory.expanduser().resolve()
    if not project.is_dir():
        print(f"error: project directory not found: {project}", file=sys.stderr)
        return 2

    checks: list[dict[str, Any]] = []
    warnings: list[str] = []
    for relative in REQUIRED_FILES:
        add_check(
            checks,
            f"required_file:{relative}",
            (project / relative).is_file(),
            (project / relative).is_file(),
            "present",
        )
    if not all(check["passed"] for check in checks):
        report = {"project": str(project), "passed": False, "checks": checks, "warnings": warnings}
        rendered = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
        if args.report:
            report_path = args.report.expanduser().resolve()
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_path.write_text(rendered, encoding="utf-8")
        print(rendered, end="")
        return 1

    try:
        state = load_json(project / "project-state.json")
        shot_plan = load_json(project / "shot-plan.json")
        manifest = load_json(project / "asset-manifest.json")
    except ValueError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    status = state.get("status")
    stage = state.get("stage")
    add_check(checks, "status", status in STATUSES, status, "one of " + ", ".join(sorted(STATUSES)))
    add_check(checks, "stage", stage in STAGES, stage, "one of " + ", ".join(sorted(STAGES)))

    assets = manifest.get("assets")
    shots = shot_plan.get("shots")
    add_check(checks, "asset_manifest_array", isinstance(assets, list), type(assets).__name__, "list")
    add_check(checks, "shot_plan_array", isinstance(shots, list) and bool(shots), type(shots).__name__, "non-empty list")
    if not isinstance(assets, list):
        assets = []
    if not isinstance(shots, list):
        shots = []

    asset_ids = [asset.get("id") for asset in assets if isinstance(asset, dict)]
    add_check(checks, "unique_asset_ids", len(asset_ids) == len(set(asset_ids)), asset_ids, "unique")
    assets_by_id = {
        asset.get("id"): asset
        for asset in assets
        if isinstance(asset, dict) and isinstance(asset.get("id"), str)
    }

    previous_end = 0.0
    for index, shot in enumerate(shots):
        if not isinstance(shot, dict):
            add_check(checks, f"shot:{index}", False, type(shot).__name__, "object")
            continue
        start = shot.get("start_seconds")
        end = shot.get("end_seconds")
        valid_times = (
            isinstance(start, (int, float))
            and isinstance(end, (int, float))
            and start >= 0
            and end > start
            and start >= previous_end
        )
        add_check(checks, f"shot:{index}:timing", valid_times, {"start": start, "end": end}, "ordered positive range")
        if isinstance(end, (int, float)):
            previous_end = float(end)
        asset_id = shot.get("asset_id")
        add_check(checks, f"shot:{index}:asset", asset_id in assets_by_id, asset_id, "manifest asset id")

    linko_assets = [asset for asset in assets_by_id.values() if asset.get("kind") == "linko-capture"]
    if not linko_assets:
        warnings.append("No Linko capture asset is currently declared.")

    capabilities = state.get("capabilities") if isinstance(state.get("capabilities"), dict) else {}
    if capabilities.get("linko_authenticated_browser") is False:
        add_check(checks, "missing_browser_status", status == "blocked", status, "blocked")
        add_check(
            checks,
            "missing_browser_blocker",
            state.get("blocker") == "authenticated-capture-unavailable",
            state.get("blocker"),
            "authenticated-capture-unavailable",
        )

    for asset in assets_by_id.values():
        for field in ("kind", "owner", "local_path", "purpose", "rights_status", "privacy_status", "placeholder", "human_approved"):
            add_check(
                checks,
                f"asset:{asset.get('id')}:{field}",
                field in asset,
                asset.get(field),
                "present",
            )

    if args.release_ready:
        add_check(checks, "release_status", status == "publish-approved", status, "publish-approved")
        add_check(checks, "release_blocker", state.get("blocker") is None, state.get("blocker"), "null")
        approvals = state.get("approvals") if isinstance(state.get("approvals"), dict) else {}
        for approval in (
            "editorial_angle",
            "script_and_shot_plan",
            "rights",
            "privacy",
            "phone_qa",
            "exact_final_file",
            "publication_destination",
        ):
            add_check(checks, f"approval:{approval}", approvals.get(approval) is True, approvals.get(approval), "true")

        add_check(checks, "final_video", (project / "render/final.mp4").is_file(), (project / "render/final.mp4").is_file(), "present")
        for asset in assets_by_id.values():
            asset_id = asset.get("id")
            add_check(checks, f"release_asset:{asset_id}:rights", asset.get("rights_status") in APPROVED_RIGHTS, asset.get("rights_status"), "approved rights state")
            add_check(checks, f"release_asset:{asset_id}:privacy", asset.get("privacy_status") in APPROVED_PRIVACY, asset.get("privacy_status"), "approved privacy state")
            add_check(checks, f"release_asset:{asset_id}:placeholder", asset.get("placeholder") is False, asset.get("placeholder"), "false")
            add_check(checks, f"release_asset:{asset_id}:human_approved", asset.get("human_approved") is True, asset.get("human_approved"), "true")
            checksum = asset.get("sha256")
            valid_checksum = (
                isinstance(checksum, str)
                and len(checksum) == 64
                and all(character in "0123456789abcdefABCDEF" for character in checksum)
            )
            add_check(checks, f"release_asset:{asset_id}:sha256", valid_checksum, checksum, "64 hexadecimal characters")
            if isinstance(asset.get("kind"), str) and asset["kind"].startswith("third-party"):
                add_check(checks, f"release_asset:{asset_id}:owner", bool(asset.get("owner")), asset.get("owner"), "non-empty")
                add_check(checks, f"release_asset:{asset_id}:canonical_url", bool(asset.get("canonical_url")), asset.get("canonical_url"), "non-empty URL")

        live_linko = any(
            asset.get("capture_mode") == "live"
            and asset.get("authenticated_session_verified") is True
            and asset.get("placeholder") is False
            for asset in linko_assets
        )
        add_check(checks, "authenticated_live_linko_capture", live_linko, live_linko, "true")
        add_check(
            checks,
            "authenticated_browser_capability",
            capabilities.get("linko_authenticated_browser") is True,
            capabilities.get("linko_authenticated_browser"),
            "true",
        )

        publish_copy = (project / "publish-copy.md").read_text(encoding="utf-8").lower()
        promises_public_linko = any(phrase in publish_copy for phrase in PUBLIC_CTA_PHRASES)
        cta = state.get("cta") if isinstance(state.get("cta"), dict) else {}
        if promises_public_linko:
            add_check(checks, "public_cta_verified", cta.get("public_destination_verified") is True, cta.get("public_destination_verified"), "true")
            add_check(checks, "public_cta_url", bool(cta.get("public_destination_url")), cta.get("public_destination_url"), "non-empty URL")

    passed = all(check["passed"] for check in checks)
    report = {
        "project": str(project),
        "mode": "release-ready" if args.release_ready else "draft-contract",
        "passed": passed,
        "status": status,
        "stage": stage,
        "checks": checks,
        "warnings": warnings,
    }
    rendered = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if args.report:
        report_path = args.report.expanduser().resolve()
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
