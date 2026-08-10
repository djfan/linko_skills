#!/usr/bin/env python3
"""Forward and negative contract tests for Linko Short release scenarios."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
SKILL = REPO / "skills" / "produce-linko-knowledge-short"
INIT = SKILL / "scripts" / "init_short_project.py"
VALIDATE = SKILL / "scripts" / "validate_project.py"
VALIDATE_SHORT = SKILL / "scripts" / "validate_short.py"


def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, check=False, capture_output=True, text=True)


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def write_publish_copy(project: Path, cta_type: str, destination: str, text: str) -> None:
    (project / "publish-copy.md").write_text(
        "---\n"
        f"cta_type: {cta_type}\n"
        f"cta_destination: {destination}\n"
        "---\n\n"
        "# Publish copy\n\n"
        "## CTA\n\n"
        f"{text}\n",
        encoding="utf-8",
    )


class ForwardContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
            raise unittest.SkipTest("FFmpeg and FFprobe are required")
        cls.sample_directory = tempfile.TemporaryDirectory()
        cls.sample_video = Path(cls.sample_directory.name) / "sample.mp4"
        result = run(
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            "color=c=blue:s=1080x1920:r=30:d=1",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:sample_rate=48000:duration=1",
            "-c:v",
            "libx264",
            "-preset",
            "ultrafast",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-shortest",
            str(cls.sample_video),
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.sample_directory.cleanup()

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.project = Path(self.temporary.name) / "short"
        result = run(sys.executable, str(INIT), str(self.project))
        self.assertEqual(result.returncode, 0, result.stderr)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def make_release_ready(self) -> None:
        state = read_json(self.project / "project-state.json")
        state["status"] = "publish-approved"
        state["stage"] = "publication-approval"
        state["capabilities"]["linko_authenticated_browser"] = True
        state["capabilities"]["ffmpeg"] = True
        for key in state["approvals"]:
            state["approvals"][key] = True
        write_json(self.project / "project-state.json", state)

        shot_plan = read_json(self.project / "shot-plan.json")
        shot_plan["format"]["target_duration_seconds"] = 1
        shot_plan["shots"][0]["end_seconds"] = 0.5
        shot_plan["shots"][1]["start_seconds"] = 0.5
        shot_plan["shots"][1]["end_seconds"] = 1
        write_json(self.project / "shot-plan.json", shot_plan)

        manifest = read_json(self.project / "asset-manifest.json")
        for asset in manifest["assets"]:
            is_source = asset["kind"] == "third-party-source"
            asset["rights_status"] = "human-approved" if is_source else "authorized"
            asset["privacy_status"] = "not-applicable" if is_source else "approved"
            asset["human_approved"] = True
            asset["sha256"] = "0" * 64
            if is_source:
                asset["owner"] = "Example publisher"
                asset["canonical_url"] = "https://example.com/source"
                asset["rights_basis"] = "Human reviewed transformative excerpt"
                asset["evidence_reference"] = {
                    "timecode": "00:00:00-00:00:01",
                    "page": None,
                    "line": None,
                    "section": None,
                    "evidence_ids": ["C1"],
                }
            if asset["kind"] == "linko-capture":
                asset["capture_mode"] = "live"
                asset["authenticated_session_verified"] = True
        write_json(self.project / "asset-manifest.json", manifest)

        final_video = self.project / "render" / "final.mp4"
        shutil.copyfile(self.sample_video, final_video)
        result = run(
            sys.executable,
            str(VALIDATE_SHORT),
            str(final_video),
            "--report",
            str(self.project / "qa" / "report.json"),
            "--min-duration",
            "0.5",
            "--max-duration",
            "2",
            "--min-lufs",
            "-40",
            "--max-lufs",
            "0",
            "--max-true-peak",
            "0",
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def validate(self, release_ready: bool = False) -> subprocess.CompletedProcess[str]:
        arguments = [sys.executable, str(VALIDATE), str(self.project)]
        if release_ready:
            arguments.append("--release-ready")
        return run(*arguments)

    def test_interview_release_contract_passes(self) -> None:
        self.make_release_ready()
        result = self.validate(release_ready=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_non_video_source_release_contract_passes(self) -> None:
        self.make_release_ready()
        manifest = read_json(self.project / "asset-manifest.json")
        source = manifest["assets"][0]
        source["kind"] = "third-party-article"
        source["excerpt_start_seconds"] = None
        source["excerpt_end_seconds"] = None
        source["evidence_reference"]["timecode"] = None
        source["evidence_reference"]["section"] = "Introduction, paragraph 4"
        write_json(self.project / "asset-manifest.json", manifest)
        result = self.validate(release_ready=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_missing_authenticated_browser_requires_exact_blocker(self) -> None:
        state = read_json(self.project / "project-state.json")
        state["status"] = "blocked"
        state["stage"] = "linko-capture"
        state["blocker"] = "authenticated-capture-unavailable"
        state["capabilities"]["linko_authenticated_browser"] = False
        write_json(self.project / "project-state.json", state)
        manifest = read_json(self.project / "asset-manifest.json")
        linko = manifest["assets"][1]
        linko["placeholder"] = True
        linko["capture_mode"] = "screenshot-prototype"
        write_json(self.project / "asset-manifest.json", manifest)
        result = self.validate()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_unclear_rights_block_release(self) -> None:
        self.make_release_ready()
        manifest = read_json(self.project / "asset-manifest.json")
        manifest["assets"][0]["rights_status"] = "pending"
        write_json(self.project / "asset-manifest.json", manifest)
        result = self.validate(release_ready=True)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn('"release_asset:primary-source:rights"', result.stdout)

    def test_empty_or_corrupt_final_video_blocks_release(self) -> None:
        for payload in (b"", b"this is not an mp4"):
            with self.subTest(payload=payload):
                self.make_release_ready()
                (self.project / "render" / "final.mp4").write_bytes(payload)
                result = self.validate(release_ready=True)
                self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                self.assertIn('"final_video_parseable"', result.stdout)

    def test_failed_or_stale_qa_report_blocks_release(self) -> None:
        self.make_release_ready()
        report_path = self.project / "qa" / "report.json"
        report = read_json(report_path)
        report["passed"] = False
        report["sha256"] = "f" * 64
        report["media"]["width"] = 720
        write_json(report_path, report)
        result = self.validate(release_ready=True)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn('"qa_report_passed"', result.stdout)
        self.assertIn('"qa_report_sha256"', result.stdout)
        self.assertIn('"qa_report_media:width"', result.stdout)

    def test_missing_evidence_locator_or_rights_basis_blocks_release(self) -> None:
        for field in ("locator", "rights_basis"):
            with self.subTest(field=field):
                self.make_release_ready()
                manifest = read_json(self.project / "asset-manifest.json")
                source = manifest["assets"][0]
                if field == "locator":
                    for key in ("timecode", "page", "line", "section"):
                        source["evidence_reference"][key] = None
                else:
                    source["rights_basis"] = ""
                write_json(self.project / "asset-manifest.json", manifest)
                result = self.validate(release_ready=True)
                self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                self.assertIn(
                    f'"release_asset:primary-source:evidence_{field}"'
                    if field == "locator"
                    else '"release_asset:primary-source:rights_basis"',
                    result.stdout,
                )

    def test_unknown_evidence_id_blocks_release(self) -> None:
        self.make_release_ready()
        manifest = read_json(self.project / "asset-manifest.json")
        manifest["assets"][0]["evidence_reference"]["evidence_ids"] = ["C99"]
        write_json(self.project / "asset-manifest.json", manifest)
        result = self.validate(release_ready=True)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn('"release_asset:primary-source:evidence_ids"', result.stdout)

    def test_public_linko_cta_variants_require_verified_destination(self) -> None:
        for wording in ("Read my notes on Linko.", "See the sources I saved in Linko."):
            with self.subTest(wording=wording):
                self.make_release_ready()
                state = read_json(self.project / "project-state.json")
                state["cta"]["type"] = "public-linko"
                state["cta"]["text"] = wording
                state["cta"]["public_destination_verified"] = False
                state["cta"]["public_destination_url"] = None
                write_json(self.project / "project-state.json", state)
                write_publish_copy(self.project, "public-linko", "", wording)
                result = self.validate(release_ready=True)
                self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                self.assertIn('"public_cta_verified"', result.stdout)

    def test_cta_type_must_match_publish_copy(self) -> None:
        self.make_release_ready()
        write_publish_copy(
            self.project,
            "public-linko",
            "https://example.com/linko/profile",
            "Read my notes on Linko.",
        )
        result = self.validate(release_ready=True)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn('"cta_type_matches_publish_copy"', result.stdout)


if __name__ == "__main__":
    unittest.main()
