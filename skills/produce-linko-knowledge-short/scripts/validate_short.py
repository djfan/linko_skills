#!/usr/bin/env python3
"""Run deterministic technical QA for a portrait knowledge Short."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


LOUDNESS_RE = re.compile(r"\{\s*\"input_i\".*?\}", re.DOTALL)
BLACK_RE = re.compile(
    r"black_start:(?P<start>[\d.]+) black_end:(?P<end>[\d.]+) "
    r"black_duration:(?P<duration>[\d.]+)"
)
SILENCE_START_RE = re.compile(r"silence_start: (?P<start>[\d.]+)")
SILENCE_END_RE = re.compile(
    r"silence_end: (?P<end>[\d.]+) \| silence_duration: (?P<duration>[\d.]+)"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("video", type=Path)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--contact-sheet", type=Path)
    parser.add_argument("--min-duration", type=float, default=40.0)
    parser.add_argument("--max-duration", type=float, default=75.0)
    parser.add_argument("--width", type=int, default=1080)
    parser.add_argument("--height", type=int, default=1920)
    parser.add_argument("--fps", type=float, help="Expected project-native delivery fps (24, 25, or 30).")
    parser.add_argument("--project-state", type=Path, help="Read delivery_fps from project-state.json.")
    parser.add_argument("--fps-tolerance", type=float, default=0.1)
    parser.add_argument("--min-lufs", type=float, default=-18.0)
    parser.add_argument("--max-lufs", type=float, default=-14.0)
    parser.add_argument("--max-true-peak", type=float, default=-1.0)
    parser.add_argument("--black-duration", type=float, default=0.30)
    parser.add_argument("--silence-duration", type=float, default=0.90)
    parser.add_argument("--silence-threshold", default="-45dB")
    parser.add_argument("--max-duplicate-ratio", type=float, default=0.02)
    parser.add_argument("--max-duplicate-run", type=int, default=1)
    return parser.parse_args()


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, check=False, capture_output=True, text=True)


def require_tools() -> list[str]:
    return [name for name in ("ffprobe", "ffmpeg") if shutil.which(name) is None]


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


def probe(video: Path) -> dict[str, Any]:
    result = run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration,size,bit_rate:stream=index,codec_name,codec_type,width,height,r_frame_rate,sample_rate,channels",
            "-of",
            "json",
            str(video),
        ]
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "ffprobe failed")
    return json.loads(result.stdout)


def measure_loudness(video: Path) -> dict[str, float]:
    result = run(
        [
            "ffmpeg",
            "-hide_banner",
            "-nostats",
            "-i",
            str(video),
            "-af",
            "loudnorm=I=-16:TP=-1.5:LRA=7:print_format=json",
            "-f",
            "null",
            "-",
        ]
    )
    match = LOUDNESS_RE.search(result.stderr)
    if not match:
        raise RuntimeError("ffmpeg did not return loudness measurements")
    payload = json.loads(match.group(0))
    return {
        "integrated_lufs": float(payload["input_i"]),
        "true_peak_dbtp": float(payload["input_tp"]),
        "loudness_range_lu": float(payload["input_lra"]),
    }


def detect_segments(
    video: Path, black_duration: float, silence_threshold: str, silence_duration: float
) -> tuple[list[dict[str, float]], list[dict[str, float]]]:
    result = run(
        [
            "ffmpeg",
            "-hide_banner",
            "-nostats",
            "-i",
            str(video),
            "-vf",
            f"blackdetect=d={black_duration}:pix_th=0.10",
            "-af",
            f"silencedetect=n={silence_threshold}:d={silence_duration}",
            "-f",
            "null",
            "-",
        ]
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "black/silence detection failed")
    black = [
        {key: float(value) for key, value in match.groupdict().items()}
        for match in BLACK_RE.finditer(result.stderr)
    ]
    starts = [float(match.group("start")) for match in SILENCE_START_RE.finditer(result.stderr)]
    ends = [
        {
            "end": float(match.group("end")),
            "duration": float(match.group("duration")),
        }
        for match in SILENCE_END_RE.finditer(result.stderr)
    ]
    silence: list[dict[str, float]] = []
    for index, end in enumerate(ends):
        start = starts[index] if index < len(starts) else end["end"] - end["duration"]
        silence.append({"start": start, **end})
    return black, silence


def measure_cadence(video: Path) -> dict[str, Any]:
    result = run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(video),
            "-map",
            "0:v:0",
            "-f",
            "framemd5",
            "-",
        ]
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "frame cadence analysis failed")
    hashes = [
        line.rsplit(",", 1)[-1].strip()
        for line in result.stdout.splitlines()
        if line and not line.startswith("#") and "," in line
    ]
    duplicate_indices = [
        index for index in range(1, len(hashes)) if hashes[index] == hashes[index - 1]
    ]
    duplicate_run = 0
    max_run = 0
    for index in range(1, len(hashes)):
        if hashes[index] == hashes[index - 1]:
            duplicate_run += 1
            max_run = max(max_run, duplicate_run)
        else:
            duplicate_run = 0
    intervals = [
        duplicate_indices[index] - duplicate_indices[index - 1]
        for index in range(1, len(duplicate_indices))
    ]
    periodic = any(
        intervals[index] == intervals[index - 1] == intervals[index - 2]
        for index in range(2, len(intervals))
    )
    return {
        "frame_count": len(hashes),
        "adjacent_exact_duplicates": len(duplicate_indices),
        "duplicate_ratio": len(duplicate_indices) / max(len(hashes) - 1, 1),
        "max_duplicate_run": max_run,
        "periodic_duplicate_cadence": periodic,
        "duplicate_indices": duplicate_indices,
    }


def expected_fps(args: argparse.Namespace) -> float:
    state_fps: Any = None
    if args.project_state:
        state_path = args.project_state.expanduser().resolve()
        try:
            state = json.loads(state_path.read_text(encoding="utf-8"))
            state_fps = state.get("delivery_fps")
        except (OSError, json.JSONDecodeError, AttributeError) as error:
            raise RuntimeError(f"cannot read project delivery_fps: {error}") from error
    if args.fps is not None and state_fps is not None and not math.isclose(args.fps, float(state_fps), abs_tol=1e-6):
        raise RuntimeError("--fps does not match project-state delivery_fps")
    value = args.fps if args.fps is not None else state_fps
    if not isinstance(value, (int, float)) or float(value) not in {24.0, 25.0, 30.0}:
        raise RuntimeError("declare delivery_fps as 24, 25, or 30 via --fps or --project-state")
    return float(value)


def make_contact_sheet(video: Path, destination: Path, duration: float) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    sample_rate = 9.0 / max(duration, 0.001)
    result = run(
        [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(video),
            "-vf",
            (
                f"fps={sample_rate:.8f},"
                "scale=270:480:force_original_aspect_ratio=decrease,"
                "pad=270:480:(ow-iw)/2:(oh-ih)/2:color=black,"
                "tile=3x3"
            ),
            "-frames:v",
            "1",
            str(destination),
        ]
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "contact-sheet generation failed")


def add_check(checks: list[dict[str, Any]], name: str, passed: bool, actual: Any, expected: str) -> None:
    checks.append(
        {"name": name, "passed": passed, "actual": actual, "expected": expected}
    )


def main() -> int:
    args = parse_args()
    video = args.video.expanduser().resolve()
    missing = require_tools()
    if missing:
        print("error: missing required tools: " + ", ".join(missing), file=sys.stderr)
        return 2
    if not video.is_file():
        print(f"error: video not found: {video}", file=sys.stderr)
        return 2

    try:
        delivery_fps = expected_fps(args)
        metadata = probe(video)
        streams = metadata.get("streams", [])
        video_stream = next(stream for stream in streams if stream.get("codec_type") == "video")
        audio_stream = next((stream for stream in streams if stream.get("codec_type") == "audio"), None)
        duration = float(metadata["format"]["duration"])
        fps = fraction(video_stream["r_frame_rate"])
        loudness = measure_loudness(video) if audio_stream else None
        black, silence = detect_segments(
            video, args.black_duration, args.silence_threshold, args.silence_duration
        )
        cadence = measure_cadence(video)
    except (KeyError, StopIteration, ValueError, RuntimeError, json.JSONDecodeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    checks: list[dict[str, Any]] = []
    add_check(
        checks,
        "duration_seconds",
        args.min_duration <= duration <= args.max_duration,
        duration,
        f"{args.min_duration}..{args.max_duration}",
    )
    add_check(checks, "width", video_stream.get("width") == args.width, video_stream.get("width"), str(args.width))
    add_check(checks, "height", video_stream.get("height") == args.height, video_stream.get("height"), str(args.height))
    add_check(checks, "fps", math.isclose(fps, delivery_fps, abs_tol=args.fps_tolerance), fps, f"{delivery_fps} ± {args.fps_tolerance}")
    expected_frames = duration * delivery_fps
    add_check(checks, "frame_count", abs(cadence["frame_count"] - expected_frames) <= 1.5, cadence["frame_count"], f"duration × {delivery_fps} ± 1.5")
    add_check(checks, "adjacent_exact_duplicates", cadence["duplicate_ratio"] <= args.max_duplicate_ratio, {"count": cadence["adjacent_exact_duplicates"], "ratio": cadence["duplicate_ratio"]}, f"ratio <= {args.max_duplicate_ratio}")
    add_check(checks, "max_duplicate_run", cadence["max_duplicate_run"] <= args.max_duplicate_run, cadence["max_duplicate_run"], f"<= {args.max_duplicate_run}")
    add_check(checks, "periodic_duplicate_cadence", cadence["periodic_duplicate_cadence"] is False, cadence["periodic_duplicate_cadence"], "false")
    add_check(checks, "audio_stream", audio_stream is not None, bool(audio_stream), "present")
    if loudness:
        add_check(
            checks,
            "integrated_lufs",
            args.min_lufs <= loudness["integrated_lufs"] <= args.max_lufs,
            loudness["integrated_lufs"],
            f"{args.min_lufs}..{args.max_lufs}",
        )
        add_check(
            checks,
            "true_peak_dbtp",
            loudness["true_peak_dbtp"] <= args.max_true_peak,
            loudness["true_peak_dbtp"],
            f"<= {args.max_true_peak}",
        )
    add_check(checks, "black_segments", not black, black, "none")
    add_check(checks, "long_silence_segments", not silence, silence, "none")

    report: dict[str, Any] = {
        "video": str(video),
        "sha256": sha256_file(video),
        "passed": all(check["passed"] for check in checks),
        "media": {
            "duration_seconds": duration,
            "size_bytes": int(metadata["format"].get("size", 0)),
            "video_codec": video_stream.get("codec_name"),
            "width": video_stream.get("width"),
            "height": video_stream.get("height"),
            "fps": fps,
            "frame_count": cadence["frame_count"],
            "audio_codec": audio_stream.get("codec_name") if audio_stream else None,
            "sample_rate": int(audio_stream.get("sample_rate", 0)) if audio_stream else None,
            "channels": audio_stream.get("channels") if audio_stream else None,
        },
        "loudness": loudness,
        "black_segments": black,
        "silence_segments": silence,
        "cadence": cadence,
        "checks": checks,
        "manual_gates": [
            "thesis and context completeness",
            "source attribution and inference boundary",
            "caption and mobile-safe visual review",
            "Linko recording authenticity and privacy",
            "third-party excerpt rights approval",
            "voice provenance and CTA truthfulness",
            "human approval of exact file and destination",
        ],
    }

    if args.contact_sheet:
        try:
            make_contact_sheet(video, args.contact_sheet.expanduser().resolve(), duration)
            report["contact_sheet"] = str(args.contact_sheet.expanduser().resolve())
        except RuntimeError as error:
            report["passed"] = False
            report["contact_sheet_error"] = str(error)

    rendered = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if args.report:
        report_path = args.report.expanduser().resolve()
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
