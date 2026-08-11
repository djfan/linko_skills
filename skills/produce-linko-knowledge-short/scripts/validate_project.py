#!/usr/bin/env python3
"""Validate a Linko knowledge Short project contract and release gates."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


REQUIRED_FILES = (
    "short-brief.md",
    "project-state.json",
    "research.md",
    "script.md",
    "shot-plan.json",
    "asset-manifest.json",
    "audio/voice-provenance.json",
    "publish-copy.md",
    "release-checklist.md",
    "qa/qa-report.md",
)

STATUSES = {"draft", "blocked", "review-ready", "publish-approved", "published"}
STAGES = {
    "preflight",
    "source-research",
    "angle-approval",
    "script-approval",
    "voice-audition",
    "source-shot-approval",
    "rights-and-privacy",
    "linko-capture-approval",
    "rough-cut",
    "automated-qa",
    "caption-phone-qa",
    "publication-approval",
    "published",
}
APPROVED_RIGHTS = {"owned", "licensed", "public-domain", "authorized", "human-approved"}
APPROVED_PRIVACY = {"approved", "not-applicable"}
CTA_TYPES = {"none", "generic", "public-linko"}
CHECKPOINTS = (
    "script_approval",
    "voice_audition",
    "source_shot_approval",
    "linko_capture_approval",
    "rough_cut",
    "caption_phone_qa",
    "release",
)
AUDIO_POLICIES = {"discard", "intentional"}
LINKO_CAPTURE_STEPS = [
    "copy-source-url",
    "open-add-link",
    "paste-submit-url",
    "resource-appears",
    "create-structured-note",
    "save-or-publish-note",
]
EVIDENCE_TYPES = {
    "SOURCE_QUOTE",
    "SOURCE_PARAPHRASE",
    "VERIFIED_CONTEXT",
    "CREATOR_INFERENCE",
}
VERIFIED_EVIDENCE_STATUSES = {"verified", "approved", "ready"}
REQUIRED_QA_CHECKS = {
    "duration_seconds",
    "width",
    "height",
    "fps",
    "frame_count",
    "adjacent_exact_duplicates",
    "max_duplicate_run",
    "periodic_duplicate_cadence",
    "audio_stream",
    "integrated_lufs",
    "true_peak_dbtp",
    "black_segments",
    "long_silence_segments",
}


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


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fraction(value: str) -> float:
    if "/" not in value:
        return float(value)
    numerator, denominator = value.split("/", 1)
    return float(numerator) / float(denominator)


def probe_media(path: Path) -> dict[str, Any]:
    if shutil.which("ffprobe") is None:
        raise RuntimeError("ffprobe is unavailable")
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration,size:stream=codec_name,codec_type,width,height,r_frame_rate,sample_rate,channels",
            "-of",
            "json",
            str(path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "ffprobe failed")
    try:
        metadata = json.loads(result.stdout)
        streams = metadata.get("streams", [])
        video_stream = next(stream for stream in streams if stream.get("codec_type") == "video")
        audio_stream = next((stream for stream in streams if stream.get("codec_type") == "audio"), None)
        return {
            "duration_seconds": float(metadata["format"]["duration"]),
            "size_bytes": int(metadata["format"].get("size", 0)),
            "video_codec": video_stream.get("codec_name"),
            "width": video_stream.get("width"),
            "height": video_stream.get("height"),
            "fps": fraction(video_stream["r_frame_rate"]),
            "audio_codec": audio_stream.get("codec_name") if audio_stream else None,
            "sample_rate": int(audio_stream.get("sample_rate", 0)) if audio_stream else None,
            "channels": audio_stream.get("channels") if audio_stream else None,
        }
    except (json.JSONDecodeError, KeyError, StopIteration, TypeError, ValueError) as error:
        raise RuntimeError(f"invalid ffprobe result: {error}") from error


def load_frontmatter(path: Path) -> dict[str, str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    values: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            return values
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        values[key.strip()] = value.strip().strip("\"'")
    return {}


def valid_http_url(value: Any) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def valid_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdefABCDEF" for character in value)
    )


def project_file(project: Path, value: Any) -> Path | None:
    if not isinstance(value, str) or not value.strip():
        return None
    candidate = (project / value).resolve()
    try:
        candidate.relative_to(project)
    except ValueError:
        return None
    return candidate


def checked_file_ref(
    checks: list[dict[str, Any]], project: Path, name: str, value: Any
) -> Path | None:
    reference = value if isinstance(value, dict) else {}
    path = project_file(project, reference.get("path"))
    checksum = reference.get("sha256")
    passed = (
        path is not None
        and path.is_file()
        and valid_sha256(checksum)
        and sha256_file(path) == checksum
    )
    add_check(checks, name, passed, reference, "existing project file with matching SHA-256")
    return path if passed else None


def values_match(expected: Any, actual: Any) -> bool:
    if isinstance(expected, (int, float)) and isinstance(actual, (int, float)):
        return math.isclose(float(expected), float(actual), rel_tol=1e-6, abs_tol=1e-6)
    return expected == actual


def evidence_ledger_row(markdown: str, identifier: str) -> dict[str, str] | None:
    for line in markdown.splitlines():
        if not line.lstrip().startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) >= 6 and cells[0] == identifier:
            return {
                "id": cells[0],
                "type": cells[1],
                "locator": cells[2],
                "evidence": cells[3],
                "planned_language": cells[4],
                "status": cells[5].lower(),
            }
    return None


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
        voice = load_json(project / "audio/voice-provenance.json")
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
    source_shot_ids: list[str] = []
    source_windows: list[tuple[str, float, float]] = []
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
        source_shot_id = shot.get("unique_source_shot_id")
        if isinstance(source_shot_id, str) and source_shot_id:
            source_shot_ids.append(source_shot_id)
        source_start = shot.get("source_start_seconds")
        source_end = shot.get("source_end_seconds")
        if (
            isinstance(asset_id, str)
            and isinstance(source_start, (int, float))
            and isinstance(source_end, (int, float))
        ):
            source_windows.append((asset_id, float(source_start), float(source_end)))

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
        for field in ("kind", "owner", "local_path", "purpose", "audio_policy", "audio_handling", "rights_status", "rights_basis", "privacy_status", "placeholder", "human_approved"):
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
            "script",
            "voice_audition",
            "source_shots",
            "rights",
            "privacy",
            "linko_capture",
            "rough_cut",
            "captions",
            "phone_qa",
            "exact_final_file",
            "publication_destination",
        ):
            add_check(checks, f"approval:{approval}", approvals.get(approval) is True, approvals.get(approval), "true")

        delivery_fps = state.get("delivery_fps")
        add_check(checks, "delivery_fps", delivery_fps in {24, 25, 30}, delivery_fps, "24, 25, or 30")
        expected_format = shot_plan.get("format") if isinstance(shot_plan.get("format"), dict) else {}
        add_check(checks, "shot_plan_delivery_fps", expected_format.get("delivery_fps") == delivery_fps, expected_format.get("delivery_fps"), repr(delivery_fps))
        cadence_state = state.get("cadence") if isinstance(state.get("cadence"), dict) else {}
        add_check(checks, "source_native_cadence", cadence_state.get("source_native_verified") is True, cadence_state.get("source_native_verified"), "true")
        fabrication_allowed = cadence_state.get("frame_fabrication_approved") is False or bool(cadence_state.get("frame_fabrication_reason"))
        add_check(checks, "frame_fabrication_policy", fabrication_allowed, cadence_state, "not approved or documented effect")

        final_video_for_dependencies = project / "render/final.mp4"
        clean_audio_for_dependencies = voice.get("clean_audio") if isinstance(voice.get("clean_audio"), dict) else {}
        dependency_values = {
            "script_sha256": sha256_file(project / "script.md"),
            "voice_sha256": clean_audio_for_dependencies.get("sha256"),
            "delivery_fps": delivery_fps,
            "ui_geometry_signature": state.get("ui_geometry_signature"),
            "final_sha256": sha256_file(final_video_for_dependencies) if final_video_for_dependencies.is_file() else None,
        }
        dependency_requirements = {
            "voice_audition": ("script_sha256",),
            "source_shot_approval": ("delivery_fps",),
            "linko_capture_approval": ("delivery_fps", "ui_geometry_signature"),
            "rough_cut": ("script_sha256", "voice_sha256", "delivery_fps"),
            "caption_phone_qa": ("voice_sha256", "delivery_fps"),
            "release": ("final_sha256",),
        }
        checkpoints = state.get("checkpoints") if isinstance(state.get("checkpoints"), dict) else {}
        for checkpoint_name in CHECKPOINTS:
            checkpoint = checkpoints.get(checkpoint_name) if isinstance(checkpoints.get(checkpoint_name), dict) else {}
            add_check(checks, f"checkpoint:{checkpoint_name}:result", checkpoint.get("result") == "PASS", checkpoint.get("result"), "PASS")
            add_check(checks, f"checkpoint:{checkpoint_name}:scope", checkpoint.get("scope") in {"candidate-asset", "final-asset"}, checkpoint.get("scope"), "candidate-asset or final-asset")
            required_approval = "release" if checkpoint_name in {"caption_phone_qa", "release"} else {"rough-cut", "release"}
            approved_for = checkpoint.get("approved_for")
            approved = approved_for == required_approval if isinstance(required_approval, str) else approved_for in required_approval
            add_check(checks, f"checkpoint:{checkpoint_name}:approved_for", approved, approved_for, "release" if isinstance(required_approval, str) else "rough-cut or release")
            artifact = {"path": checkpoint.get("artifact_path"), "sha256": checkpoint.get("sha256")}
            checked_file_ref(checks, project, f"checkpoint:{checkpoint_name}:artifact", artifact)
            lock = checkpoint.get("dependency_lock") if isinstance(checkpoint.get("dependency_lock"), dict) else {}
            for dependency in dependency_requirements.get(checkpoint_name, ()):
                add_check(checks, f"checkpoint:{checkpoint_name}:dependency:{dependency}", lock.get(dependency) == dependency_values.get(dependency) and dependency_values.get(dependency) not in (None, ""), lock.get(dependency), repr(dependency_values.get(dependency)))

        risk_proofs = state.get("risk_proofs") if isinstance(state.get("risk_proofs"), dict) else {}
        for proof_name in ("motion_capture", "active_picture_crop", "vertical_reframe", "linko_flow", "final_note_framing"):
            proof = risk_proofs.get(proof_name) if isinstance(risk_proofs.get(proof_name), dict) else {}
            add_check(checks, f"risk_proof:{proof_name}:result", proof.get("result") == "PASS", proof.get("result"), "PASS")
            checked_file_ref(checks, project, f"risk_proof:{proof_name}:artifact", {"path": proof.get("artifact_path"), "sha256": proof.get("sha256")})
        bridge_proof = risk_proofs.get("authored_bridge") if isinstance(risk_proofs.get("authored_bridge"), dict) else {}
        if bridge_proof.get("required") is True:
            add_check(checks, "risk_proof:authored_bridge:result", bridge_proof.get("result") == "PASS", bridge_proof.get("result"), "PASS")
            checked_file_ref(checks, project, "risk_proof:authored_bridge:artifact", {"path": bridge_proof.get("artifact_path"), "sha256": bridge_proof.get("sha256")})

        editorial_review = state.get("editorial_review") if isinstance(state.get("editorial_review"), dict) else {}
        add_check(
            checks,
            "source_mode_not_changed_since_approval",
            editorial_review.get("source_mode_changed_since_script_approval") is False,
            editorial_review.get("source_mode_changed_since_script_approval"),
            "false after any required reapproval",
        )
        add_check(checks, "cold_read_context", editorial_review.get("cold_read_context_passed") is True, editorial_review.get("cold_read_context_passed"), "true")
        add_check(checks, "evidence_boundary", editorial_review.get("evidence_boundary_approved") is True, editorial_review.get("evidence_boundary_approved"), "true")
        add_check(checks, "first_person_premise", editorial_review.get("first_person_premise_verified") is True, editorial_review.get("first_person_premise_verified"), "true")
        add_check(checks, "saved_object", bool(editorial_review.get("saved_object")), editorial_review.get("saved_object"), "non-empty truthful saved object")

        deliverable = state.get("deliverable") if isinstance(state.get("deliverable"), dict) else {}
        deliverable_type = deliverable.get("type")
        add_check(checks, "deliverable_type", deliverable_type in {"main", "cutdown"}, deliverable_type, "main or cutdown")
        if deliverable_type == "cutdown":
            add_check(checks, "cutdown_parent_project", bool(deliverable.get("parent_project")), deliverable.get("parent_project"), "non-empty parent project")
            add_check(checks, "cutdown_dedicated_script", deliverable.get("dedicated_script_approved") is True, deliverable.get("dedicated_script_approved"), "true")

        add_check(checks, "unique_source_shot_ids", len(source_shot_ids) == len(shots) and len(source_shot_ids) == len(set(source_shot_ids)), source_shot_ids, "one unique non-empty ID per shot")
        add_check(checks, "unique_source_windows", len(source_windows) == len(shots) and len(source_windows) == len(set(source_windows)), source_windows, "one unique source time window per shot")
        for index, shot in enumerate(shots):
            if not isinstance(shot, dict):
                continue
            source_start = shot.get("source_start_seconds")
            source_end = shot.get("source_end_seconds")
            add_check(
                checks,
                f"release_shot:{index}:source_range",
                isinstance(source_start, (int, float)) and isinstance(source_end, (int, float)) and source_start >= 0 and source_end > source_start,
                {"start": source_start, "end": source_end},
                "ordered non-negative source range",
            )
            add_check(checks, f"release_shot:{index}:visual_role", bool(shot.get("visual_role")), shot.get("visual_role"), "non-empty")
            add_check(checks, f"release_shot:{index}:audio_policy", shot.get("audio_policy") in AUDIO_POLICIES, shot.get("audio_policy"), "discard or intentional")
            motion = shot.get("motion_validation") if isinstance(shot.get("motion_validation"), dict) else {}
            add_check(checks, f"release_shot:{index}:timeline_progression", motion.get("current_time_progressed") is True, motion.get("current_time_progressed"), "true")
            add_check(checks, f"release_shot:{index}:dynamic_frames", motion.get("first_middle_final_pixel_change") is True, motion.get("first_middle_final_pixel_change"), "true")
            add_check(checks, f"release_shot:{index}:continuous_motion", motion.get("continuous_motion_source") is True, motion.get("continuous_motion_source"), "true")
            add_check(checks, f"release_shot:{index}:not_screenshot_sequence", motion.get("screenshot_sequence") is False, motion.get("screenshot_sequence"), "false")
            expected_shot_frames = (source_end - source_start) * delivery_fps if isinstance(source_start, (int, float)) and isinstance(source_end, (int, float)) and isinstance(delivery_fps, (int, float)) else None
            add_check(checks, f"release_shot:{index}:frame_count", isinstance(motion.get("frame_count"), int) and expected_shot_frames is not None and abs(motion.get("frame_count") - expected_shot_frames) <= 1, motion.get("frame_count"), f"source duration × fps ± 1 ({expected_shot_frames})")
            add_check(checks, f"release_shot:{index}:duplicate_run", isinstance(motion.get("max_duplicate_run"), int) and motion.get("max_duplicate_run") <= 1, motion.get("max_duplicate_run"), "<= 1")
            add_check(checks, f"release_shot:{index}:periodic_duplicates", motion.get("periodic_duplicates_detected") is False, motion.get("periodic_duplicates_detected"), "false")
            source_media = shot.get("source_media") if isinstance(shot.get("source_media"), dict) else {}
            decoded_ok = all(isinstance(source_media.get(field), int) and source_media.get(field) > 0 for field in ("decoded_width", "decoded_height", "active_width", "active_height", "crop_width", "crop_height"))
            add_check(checks, f"release_shot:{index}:source_dimensions", decoded_ok, source_media, "positive decoded, active-picture, and crop dimensions")
            effective_pixels_ok = decoded_ok and source_media.get("active_width") >= 1280 and source_media.get("active_height") >= 720 and source_media.get("crop_width") >= 360 and source_media.get("crop_height") >= 640
            add_check(checks, f"release_shot:{index}:effective_source_pixels", effective_pixels_ok, source_media, "active >= 1280x720 and crop >= 360x640")
            add_check(checks, f"release_shot:{index}:upscale_ratio", isinstance(source_media.get("upscale_ratio"), (int, float)) and 0 < source_media.get("upscale_ratio") <= 3.0, source_media.get("upscale_ratio"), "0 < ratio <= 3.0")
            add_check(checks, f"release_shot:{index}:source_fps", source_media.get("source_fps") == delivery_fps, source_media.get("source_fps"), repr(delivery_fps))
            add_check(checks, f"release_shot:{index}:capture_fps", source_media.get("capture_fps") == delivery_fps, source_media.get("capture_fps"), repr(delivery_fps))
            add_check(checks, f"release_shot:{index}:capture_transport", source_media.get("capture_transport") in {"viewport", "native-screen", "video-capture-stream", "browser-screencast", "source-file"}, source_media.get("capture_transport"), "approved capture transport")
            add_check(checks, f"release_shot:{index}:reframe_strategy", shot.get("reframe_strategy") in {"subject-aware-crop", "clean-edge-extension", "fit"}, shot.get("reframe_strategy"), "subject-aware-crop, clean-edge-extension, or fit")
            for field in ("subject_safe_space_reviewed", "player_ui_absent", "black_edges_absent", "not_stretched"):
                add_check(checks, f"release_shot:{index}:{field}", shot.get(field) is True, shot.get(field), "true")
            add_check(checks, f"release_shot:{index}:burned_text", shot.get("burned_text_status") in {"none", "cleanly-cropped"}, shot.get("burned_text_status"), "none or cleanly-cropped")
            crop_evidence = project_file(project, shot.get("crop_100_percent_evidence"))
            add_check(checks, f"release_shot:{index}:crop_evidence", crop_evidence is not None and crop_evidence.is_file(), shot.get("crop_100_percent_evidence"), "existing 100% crop evidence")

        source_review = shot_plan.get("source_shot_review") if isinstance(shot_plan.get("source_shot_review"), dict) else {}
        add_check(checks, "source_shot_review_approved", source_review.get("approved") is True, source_review.get("approved"), "true")
        for field in ("contact_sheet", "timecode_table"):
            path = project_file(project, source_review.get(field))
            add_check(checks, f"source_shot_review:{field}", path is not None and path.is_file(), source_review.get(field), "existing project file")

        audio_render = manifest.get("audio_render") if isinstance(manifest.get("audio_render"), dict) else {}
        approved_tracks = audio_render.get("approved_tracks")
        add_check(checks, "audio_render:approved_tracks", isinstance(approved_tracks, list) and bool(approved_tracks) and all(isinstance(track, str) and track.strip() for track in approved_tracks), approved_tracks, "non-empty approved track list")
        add_check(checks, "audio_render:ffprobe_verified", audio_render.get("ffprobe_verified") is True, audio_render.get("ffprobe_verified"), "true")
        add_check(checks, "audio_render:filter_graph_reviewed", audio_render.get("filter_graph_reviewed") is True, audio_render.get("filter_graph_reviewed"), "true")
        music_allowed = audio_render.get("first_rough_cut_includes_music") is False or audio_render.get("music_required_by_brief") is True
        add_check(checks, "audio_render:first_rough_cut_music", music_allowed, {"includes_music": audio_render.get("first_rough_cut_includes_music"), "required_by_brief": audio_render.get("music_required_by_brief")}, "no music unless required by brief")

        for field in ("provider", "model", "voice_id", "performance_instructions", "generated_at"):
            add_check(checks, f"voice:{field}", isinstance(voice.get(field), str) and bool(voice.get(field, "").strip()), voice.get(field), "non-empty")
        add_check(checks, "voice:speed", isinstance(voice.get("speed"), (int, float)) and voice.get("speed") > 0, voice.get("speed"), "> 0")
        add_check(checks, "voice:generation_mode", voice.get("generation_mode") in {"full-script", "segmented"}, voice.get("generation_mode"), "full-script or segmented")
        if voice.get("generation_mode") == "segmented":
            add_check(checks, "voice:split_reason", bool(voice.get("split_reason")), voice.get("split_reason"), "non-empty reason")
        add_check(checks, "voice:take_count", isinstance(voice.get("take_count"), int) and voice.get("take_count") > 0, voice.get("take_count"), "> 0")
        add_check(checks, "voice:selected_take", isinstance(voice.get("selected_take"), int) and 1 <= voice.get("selected_take") <= voice.get("take_count", 0), voice.get("selected_take"), "between 1 and take_count")
        add_check(checks, "voice:auditioned_without_music", voice.get("auditioned_without_music") is True, voice.get("auditioned_without_music"), "true")
        add_check(checks, "voice:human_approved", voice.get("human_approved") is True, voice.get("human_approved"), "true")
        for variant in ("raw_audio", "clean_audio"):
            artifact = voice.get(variant) if isinstance(voice.get(variant), dict) else {}
            path = project_file(project, artifact.get("path"))
            checksum = artifact.get("sha256")
            add_check(checks, f"voice:{variant}:file", path is not None and path.is_file(), artifact.get("path"), "existing project file")
            add_check(checks, f"voice:{variant}:sha256", path is not None and path.is_file() and valid_sha256(checksum) and sha256_file(path) == checksum, checksum, "hash of voice artifact")
        time_stretch = voice.get("time_stretch") if isinstance(voice.get("time_stretch"), dict) else {}
        add_check(checks, "voice:no_unjustified_time_stretch", time_stretch.get("used") is False or bool(time_stretch.get("reason")), time_stretch, "unused or documented reason")
        clean_voice = voice.get("clean_audio") if isinstance(voice.get("clean_audio"), dict) else {}
        add_check(checks, "voice:locked_take_hash", voice.get("selected_take_locked_sha256") == clean_voice.get("sha256") and valid_sha256(voice.get("selected_take_locked_sha256")), voice.get("selected_take_locked_sha256"), "approved clean-audio SHA-256")
        word_count = voice.get("script_word_count")
        actual_duration = voice.get("actual_duration_seconds")
        actual_wpm = voice.get("actual_wpm")
        measured_wpm = word_count / actual_duration * 60 if isinstance(word_count, int) and word_count > 0 and isinstance(actual_duration, (int, float)) and actual_duration > 0 else None
        add_check(checks, "voice:measured_pacing", measured_wpm is not None and isinstance(actual_wpm, (int, float)) and math.isclose(actual_wpm, measured_wpm, abs_tol=0.5), actual_wpm, repr(measured_wpm))
        add_check(checks, "voice:pause_brief", bool(voice.get("pause_brief")), voice.get("pause_brief"), "non-empty")
        transcript = voice.get("transcript") if isinstance(voice.get("transcript"), dict) else {}
        checked_file_ref(checks, project, "voice:transcript", transcript)
        add_check(checks, "voice:transcript_drift", isinstance(transcript.get("wer"), (int, float)) and 0 <= transcript.get("wer") <= 0.02, transcript.get("wer"), "0..0.02")
        pronunciations = voice.get("pronunciation_checklist")
        pronunciations_ok = isinstance(pronunciations, list) and bool(pronunciations) and all(isinstance(item, dict) and item.get("status") == "approved" and bool(item.get("term")) for item in pronunciations)
        add_check(checks, "voice:pronunciation_review", pronunciations_ok, pronunciations, "non-empty approved checklist")
        add_check(checks, "voice:long_pause_count", isinstance(voice.get("long_pause_count"), int) and voice.get("long_pause_count") >= 0, voice.get("long_pause_count"), ">= 0")
        add_check(checks, "voice:audition_decision", voice.get("audition_decision") == "PASS", voice.get("audition_decision"), "PASS")
        add_check(checks, "voice:audible_traits_only", voice.get("audible_traits_only") is True, voice.get("audible_traits_only"), "true")
        target_wpm = voice.get("target_wpm") if isinstance(voice.get("target_wpm"), dict) else {}
        in_target = isinstance(actual_wpm, (int, float)) and isinstance(target_wpm.get("min"), (int, float)) and isinstance(target_wpm.get("max"), (int, float)) and target_wpm.get("min") <= actual_wpm <= target_wpm.get("max")
        add_check(checks, "voice:pacing_target_or_override", in_target or bool(voice.get("creative_spec_override")), {"actual_wpm": actual_wpm, "target": target_wpm, "override": voice.get("creative_spec_override")}, "within target or explicit override")

        captions = shot_plan.get("captions") if isinstance(shot_plan.get("captions"), dict) else {}
        clean_audio = voice.get("clean_audio") if isinstance(voice.get("clean_audio"), dict) else {}
        add_check(checks, "captions:waveform_binding", valid_sha256(captions.get("waveform_sha256")) and captions.get("waveform_sha256") == clean_audio.get("sha256"), captions.get("waveform_sha256"), "approved clean-audio SHA-256")
        for field in ("timing_manually_corrected", "phone_sound_qa", "phone_muted_qa"):
            add_check(checks, f"captions:{field}", captions.get(field) is True, captions.get(field), "true")
        add_check(checks, "captions:max_lines", captions.get("max_lines") == 2, captions.get("max_lines"), "2")
        checked_file_ref(checks, project, "captions:alignment", captions.get("alignment"))
        add_check(checks, "captions:event_count", isinstance(captions.get("event_count"), int) and captions.get("event_count") > 0, captions.get("event_count"), "> 0")
        style = captions.get("style") if isinstance(captions.get("style"), dict) else {}
        add_check(checks, "captions:style", bool(style.get("font")) and isinstance(style.get("size_px"), (int, float)) and style.get("size_px") > 0, style, "font and positive size")
        add_check(checks, "captions:highlight_count", isinstance(captions.get("highlight_count"), int) and 0 <= captions.get("highlight_count") <= captions.get("event_count", -1), captions.get("highlight_count"), "0..event_count")
        collision = captions.get("collision_review") if isinstance(captions.get("collision_review"), dict) else {}
        for field in ("burned_source_text_reviewed", "platform_controls_reviewed"):
            add_check(checks, f"captions:collision:{field}", collision.get(field) is True, collision.get(field), "true")
        for field in ("first_frame", "middle_frame", "final_frame"):
            evidence_path = project_file(project, collision.get(field))
            add_check(checks, f"captions:collision:{field}", evidence_path is not None and evidence_path.is_file(), collision.get(field), "existing evidence frame")
        platform_export = captions.get("platform_export") if isinstance(captions.get("platform_export"), dict) else {}
        if platform_export.get("path") or platform_export.get("sha256"):
            checked_file_ref(checks, project, "captions:platform_export", platform_export)

        final_video = project / "render/final.mp4"
        final_exists = final_video.is_file()
        add_check(checks, "final_video", final_exists, final_exists, "present")
        final_nonempty = final_exists and final_video.stat().st_size > 0
        add_check(
            checks,
            "final_video_nonempty",
            final_nonempty,
            final_video.stat().st_size if final_exists else None,
            "> 0 bytes",
        )

        probed_media: dict[str, Any] | None = None
        probe_error: str | None = None
        if final_nonempty:
            try:
                probed_media = probe_media(final_video)
            except RuntimeError as error:
                probe_error = str(error)
        add_check(
            checks,
            "final_video_parseable",
            probed_media is not None,
            probed_media if probed_media is not None else probe_error,
            "parseable video and audio media",
        )

        qa_report_path = project / "qa/report.json"
        qa_report: dict[str, Any] | None = None
        qa_error: str | None = None
        if qa_report_path.is_file():
            try:
                qa_report = load_json(qa_report_path)
            except ValueError as error:
                qa_error = str(error)
        add_check(checks, "qa_report", qa_report is not None, qa_error, "valid qa/report.json")
        if qa_report is not None:
            add_check(checks, "qa_report_passed", qa_report.get("passed") is True, qa_report.get("passed"), "true")
            qa_checks = qa_report.get("checks") if isinstance(qa_report.get("checks"), list) else []
            qa_check_names = {
                check.get("name")
                for check in qa_checks
                if isinstance(check, dict) and isinstance(check.get("name"), str)
            }
            qa_checks_passed = bool(qa_checks) and all(
                isinstance(check, dict) and check.get("passed") is True
                for check in qa_checks
            )
            add_check(checks, "qa_report_checks_passed", qa_checks_passed, qa_checks, "non-empty list with every check passed")
            add_check(
                checks,
                "qa_report_checks_complete",
                REQUIRED_QA_CHECKS.issubset(qa_check_names),
                sorted(name for name in qa_check_names if isinstance(name, str)),
                "all required technical QA check names",
            )
            qa_video = qa_report.get("video")
            qa_video_matches = False
            if isinstance(qa_video, str):
                try:
                    qa_video_matches = Path(qa_video).expanduser().resolve() == final_video.resolve()
                except OSError:
                    qa_video_matches = False
            add_check(checks, "qa_report_video", qa_video_matches, qa_video, str(final_video.resolve()))
            actual_final_hash = sha256_file(final_video) if final_exists else None
            add_check(
                checks,
                "qa_report_sha256",
                qa_report.get("sha256") == actual_final_hash and actual_final_hash is not None,
                qa_report.get("sha256"),
                actual_final_hash or "hash of final video",
            )
            qa_media = qa_report.get("media") if isinstance(qa_report.get("media"), dict) else {}
            if probed_media is not None:
                for field, actual in probed_media.items():
                    add_check(
                        checks,
                        f"qa_report_media:{field}",
                        field in qa_media and values_match(qa_media.get(field), actual),
                        qa_media.get(field),
                        repr(actual),
                    )
                add_check(
                    checks,
                    "final_audio_stream",
                    bool(probed_media.get("audio_codec")),
                    probed_media.get("audio_codec"),
                    "present",
                )

        expected_format = shot_plan.get("format") if isinstance(shot_plan.get("format"), dict) else {}
        if probed_media is not None:
            for field in ("width", "height"):
                add_check(
                    checks,
                    f"final_format:{field}",
                    field in expected_format and values_match(expected_format.get(field), probed_media.get(field)),
                    probed_media.get(field),
                    repr(expected_format.get(field)),
                )
            add_check(checks, "final_format:fps", values_match(delivery_fps, probed_media.get("fps")), probed_media.get("fps"), repr(delivery_fps))

        research = (project / "research.md").read_text(encoding="utf-8")
        for asset in assets_by_id.values():
            asset_id = asset.get("id")
            add_check(checks, f"release_asset:{asset_id}:rights", asset.get("rights_status") in APPROVED_RIGHTS, asset.get("rights_status"), "approved rights state")
            add_check(checks, f"release_asset:{asset_id}:privacy", asset.get("privacy_status") in APPROVED_PRIVACY, asset.get("privacy_status"), "approved privacy state")
            add_check(checks, f"release_asset:{asset_id}:placeholder", asset.get("placeholder") is False, asset.get("placeholder"), "false")
            add_check(checks, f"release_asset:{asset_id}:human_approved", asset.get("human_approved") is True, asset.get("human_approved"), "true")
            checksum = asset.get("sha256")
            add_check(checks, f"release_asset:{asset_id}:sha256", valid_sha256(checksum), checksum, "64 hexadecimal characters")
            audio_policy = asset.get("audio_policy")
            audio_handling = asset.get("audio_handling") if isinstance(asset.get("audio_handling"), dict) else {}
            add_check(checks, f"release_asset:{asset_id}:audio_policy", audio_policy in AUDIO_POLICIES, audio_policy, "discard or intentional")
            if audio_policy == "discard":
                add_check(checks, f"release_asset:{asset_id}:input_audio_removed", audio_handling.get("input_audio_removed") is True, audio_handling.get("input_audio_removed"), "true")
            elif audio_policy == "intentional":
                add_check(checks, f"release_asset:{asset_id}:approved_mix_track", bool(audio_handling.get("approved_mix_track")), audio_handling.get("approved_mix_track"), "non-empty")
                add_check(checks, f"release_asset:{asset_id}:loudness_reviewed", audio_handling.get("loudness_reviewed") is True, audio_handling.get("loudness_reviewed"), "true")
                add_check(checks, f"release_asset:{asset_id}:transition_reviewed", audio_handling.get("transition_reviewed") is True, audio_handling.get("transition_reviewed"), "true")
            intentional_shot = any(
                isinstance(shot, dict)
                and shot.get("asset_id") == asset_id
                and shot.get("audio_policy") == "intentional"
                for shot in shots
            )
            if intentional_shot:
                add_check(checks, f"release_asset:{asset_id}:intentional_audio_declared", audio_policy == "intentional", audio_policy, "intentional")
            if isinstance(asset.get("kind"), str) and asset["kind"].startswith("third-party"):
                add_check(checks, f"release_asset:{asset_id}:owner", bool(asset.get("owner")), asset.get("owner"), "non-empty")
                add_check(checks, f"release_asset:{asset_id}:canonical_url", valid_http_url(asset.get("canonical_url")), asset.get("canonical_url"), "valid http(s) URL")
                add_check(checks, f"release_asset:{asset_id}:rights_basis", bool(asset.get("rights_basis")), asset.get("rights_basis"), "non-empty reviewed basis")
                evidence = asset.get("evidence_reference") if isinstance(asset.get("evidence_reference"), dict) else {}
                locators = {key: evidence.get(key) for key in ("timecode", "page", "line", "section")}
                has_locator = any(value not in (None, "", []) for value in locators.values())
                add_check(checks, f"release_asset:{asset_id}:evidence_locator", has_locator, locators, "at least one timecode, page, line, or section")
                evidence_ids = evidence.get("evidence_ids") if isinstance(evidence.get("evidence_ids"), list) else []
                structured_locators = {
                    str(value).strip()
                    for value in locators.values()
                    if value not in (None, "", [])
                }
                valid_ids = bool(evidence_ids)
                for identifier in evidence_ids:
                    identifier_valid = isinstance(identifier, str) and bool(identifier.strip())
                    row = evidence_ledger_row(research, identifier) if identifier_valid else None
                    row_valid = bool(
                        row
                        and row["type"] in EVIDENCE_TYPES
                        and row["locator"] in structured_locators
                        and row["evidence"]
                        and row["planned_language"]
                        and row["status"] in VERIFIED_EVIDENCE_STATUSES
                    )
                    add_check(
                        checks,
                        f"release_asset:{asset_id}:evidence_ledger:{identifier}",
                        row_valid,
                        row,
                        "complete verified ledger row with matching locator",
                    )
                    valid_ids = valid_ids and identifier_valid and row_valid
                add_check(checks, f"release_asset:{asset_id}:evidence_ids", valid_ids, evidence_ids, "non-empty IDs present in research.md")
            if asset.get("kind") == "authored-bridge":
                add_check(checks, f"bridge:{asset_id}:asset_type", asset.get("asset_type") == "authored-bridge", asset.get("asset_type"), "authored-bridge")
                add_check(checks, f"bridge:{asset_id}:truth_boundary", asset.get("claims_product_success") is False and asset.get("ends_before_real_action") is True, {"claims_product_success": asset.get("claims_product_success"), "ends_before_real_action": asset.get("ends_before_real_action")}, "no product success claim and stop before real action")
                match_cut = asset.get("match_cut") if isinstance(asset.get("match_cut"), dict) else {}
                add_check(checks, f"bridge:{asset_id}:real_linko_target", match_cut.get("real_asset_id") in {item.get("id") for item in linko_assets}, match_cut.get("real_asset_id"), "Linko capture asset id")
                for field in ("fps_match", "geometry_match", "text_match", "url_state_match", "button_state_match"):
                    add_check(checks, f"bridge:{asset_id}:{field}", match_cut.get(field) is True, match_cut.get(field), "true")
                checked_file_ref(checks, project, f"bridge:{asset_id}:match_proof", match_cut.get("proof"))

        live_linko = any(
            asset.get("capture_mode") == "continuous-master"
            and asset.get("capture_transport") in {"native-screen-recording", "browser-screencast"}
            and asset.get("capture_steps") == LINKO_CAPTURE_STEPS
            and asset.get("timeline_progression_verified") is True
            and asset.get("dynamic_frames_verified") is True
            and asset.get("authenticated_session_verified") is True
            and asset.get("placeholder") is False
            for asset in linko_assets
        )
        add_check(checks, "authenticated_continuous_linko_capture", live_linko, live_linko, "true")
        add_check(
            checks,
            "authenticated_browser_capability",
            capabilities.get("linko_authenticated_browser") is True,
            capabilities.get("linko_authenticated_browser"),
            "true",
        )
        for asset in linko_assets:
            asset_id = asset.get("id")
            for field in ("raw_master", "edited_cut", "edit_decision_list"):
                checked_file_ref(checks, project, f"linko:{asset_id}:{field}", asset.get(field))
            transition = asset.get("transition_integrity") if isinstance(asset.get("transition_integrity"), dict) else {}
            for field in ("clicks", "pointer_motion", "scrolls", "loading_to_success", "resource_appearance", "save_state_change"):
                add_check(checks, f"linko:{asset_id}:transition:{field}", transition.get(field) is True, transition.get(field), "true")
            semantic = asset.get("semantic_qa") if isinstance(asset.get("semantic_qa"), dict) else {}
            add_check(checks, f"linko:{asset_id}:saved_object", semantic.get("saved_object") == editorial_review.get("saved_object") and bool(semantic.get("saved_object")), semantic.get("saved_object"), repr(editorial_review.get("saved_object")))
            for field in ("note_title_readable", "requested_hierarchy_readable", "open_question_readable", "no_post_production_tag_overlay"):
                add_check(checks, f"linko:{asset_id}:semantic:{field}", semantic.get(field) is True, semantic.get(field), "true")
            if semantic.get("requested_note_tag"):
                add_check(checks, f"linko:{asset_id}:note_tag_owner", semantic.get("note_tag_owner_verified_in_ui") is True, semantic.get("note_tag_owner_verified_in_ui"), "true")

        cta = state.get("cta") if isinstance(state.get("cta"), dict) else {}
        cta_type = cta.get("type")
        publish_frontmatter = load_frontmatter(project / "publish-copy.md")
        publish_cta_type = publish_frontmatter.get("cta_type")
        add_check(checks, "cta_type", cta_type in CTA_TYPES, cta_type, "none, generic, or public-linko")
        add_check(checks, "publish_cta_type", publish_cta_type in CTA_TYPES, publish_cta_type, "none, generic, or public-linko")
        add_check(checks, "cta_type_matches_publish_copy", publish_cta_type == cta_type, publish_cta_type, repr(cta_type))
        if cta_type == "public-linko":
            add_check(checks, "public_cta_verified", cta.get("public_destination_verified") is True, cta.get("public_destination_verified"), "true")
            state_destination = cta.get("public_destination_url")
            publish_destination = publish_frontmatter.get("cta_destination")
            add_check(checks, "public_cta_url", valid_http_url(state_destination), state_destination, "valid http(s) URL")
            add_check(checks, "public_cta_destination_matches", publish_destination == state_destination, publish_destination, repr(state_destination))

        publishing_fields = (
            "primary_title",
            "title_variant_a",
            "title_variant_b",
            "language",
            "category",
            "audience",
            "paid_promotion_decision",
            "remixing_decision",
            "related_video",
            "visibility",
            "cover_timestamp",
            "cover_proof_path",
            "policy_verified_at",
            "description_ready",
            "hashtags",
            "studio_tags",
            "source_attribution_ready",
            "synthetic_altered_content_decision",
            "pinned_comment",
            "audience_question",
            "platform_link_behavior",
        )
        for field in publishing_fields:
            add_check(checks, f"publishing:{field}", isinstance(publish_frontmatter.get(field), str) and bool(publish_frontmatter.get(field, "").strip()), publish_frontmatter.get(field), "non-empty")
        cover_proof = project_file(project, publish_frontmatter.get("cover_proof_path"))
        add_check(checks, "publishing:cover_proof", cover_proof is not None and cover_proof.is_file(), publish_frontmatter.get("cover_proof_path"), "existing project file")

        post_lock = state.get("post_lock_revision") if isinstance(state.get("post_lock_revision"), dict) else {}
        if post_lock.get("active") is True:
            for field in ("prior_canonical", "scoped_proof", "full_candidate"):
                checked_file_ref(checks, project, f"post_lock:{field}", post_lock.get(field))
            add_check(checks, "post_lock:changed_region", bool(post_lock.get("changed_region")), post_lock.get("changed_region"), "non-empty")
            for field in ("continuity_boundaries_reviewed", "unchanged_streams_or_ranges_verified", "candidate_passed", "canonical_replaced", "exact_file_qa_renewed"):
                add_check(checks, f"post_lock:{field}", post_lock.get(field) is True, post_lock.get(field), "true")

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
