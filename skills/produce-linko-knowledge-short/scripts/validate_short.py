#!/usr/bin/env python3
"""Run deterministic technical QA for a portrait knowledge Short."""

from __future__ import annotations

import argparse
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
    parser.add_argument("--fps", type=float, default=30.0)
    parser.add_argument("--fps-tolerance", type=float, default=0.1)
    parser.add_argument("--min-lufs", type=float, default=-18.0)
    parser.add_argument("--max-lufs", type=float, default=-14.0)
    parser.add_argument("--max-true-peak", type=float, default=-1.0)
    parser.add_argument("--black-duration", type=float, default=0.30)
    parser.add_argument("--silence-duration", type=float, default=0.90)
    parser.add_argument("--silence-threshold", default="-45dB")
    return parser.parse_args()


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, check=False, capture_output=True, text=True)


def require_tools() -> list[str]:
    return [name for name in ("ffprobe", "ffmpeg") if shutil.which(name) is None]


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
    add_check(checks, "fps", math.isclose(fps, args.fps, abs_tol=args.fps_tolerance), fps, f"{args.fps} ± {args.fps_tolerance}")
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
        "passed": all(check["passed"] for check in checks),
        "media": {
            "duration_seconds": duration,
            "size_bytes": int(metadata["format"].get("size", 0)),
            "video_codec": video_stream.get("codec_name"),
            "width": video_stream.get("width"),
            "height": video_stream.get("height"),
            "fps": fps,
            "audio_codec": audio_stream.get("codec_name") if audio_stream else None,
            "sample_rate": int(audio_stream.get("sample_rate", 0)) if audio_stream else None,
            "channels": audio_stream.get("channels") if audio_stream else None,
        },
        "loudness": loudness,
        "black_segments": black,
        "silence_segments": silence,
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
