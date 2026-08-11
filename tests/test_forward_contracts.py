#!/usr/bin/env python3
"""Forward and negative contract tests for Linko Short release scenarios."""

from __future__ import annotations

import hashlib
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


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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


def set_research_evidence(project: Path, locator: str) -> None:
    path = project / "research.md"
    content = path.read_text(encoding="utf-8")
    content = content.replace(
        "| C1 | SOURCE_QUOTE | | | | pending |",
        f"| C1 | SOURCE_QUOTE | {locator} | Example verified statement. | Example script language. | verified |",
    )
    path.write_text(content, encoding="utf-8")


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
        state["editorial_review"]["cold_read_context_passed"] = True
        state["editorial_review"]["evidence_boundary_approved"] = True
        for key in state["approvals"]:
            state["approvals"][key] = True
        for name, checkpoint in state["checkpoints"].items():
            checkpoint["result"] = "PASS"
            checkpoint["evidence"] = f"qa/{name}.md"
        write_json(self.project / "project-state.json", state)

        shot_plan = read_json(self.project / "shot-plan.json")
        shot_plan["format"]["target_duration_seconds"] = 1
        shot_plan["shots"][0]["end_seconds"] = 0.5
        shot_plan["shots"][1]["start_seconds"] = 0.5
        shot_plan["shots"][1]["end_seconds"] = 1
        shot_plan["shots"][0]["source_end_seconds"] = 0.5
        shot_plan["shots"][1]["source_start_seconds"] = 0.5
        shot_plan["shots"][1]["source_end_seconds"] = 1
        for shot in shot_plan["shots"]:
            shot["motion_validation"]["current_time_progressed"] = True
            shot["motion_validation"]["first_middle_final_pixel_change"] = True
        shot_plan["source_shot_review"]["approved"] = True
        (self.project / "qa" / "source-shot-contact-sheet.png").write_bytes(b"contact sheet")
        (self.project / "qa" / "source-shot-timecodes.md").write_text("# Source shot timecodes\n", encoding="utf-8")

        raw_voice = self.project / "audio" / "voice-raw.m4a"
        clean_voice = self.project / "audio" / "voice-clean.m4a"
        shutil.copyfile(self.sample_video, raw_voice)
        shutil.copyfile(self.sample_video, clean_voice)
        voice = read_json(self.project / "audio" / "voice-provenance.json")
        voice.update(
            {
                "provider": "Example voice provider",
                "model": "example-model",
                "voice_id": "example-voice",
                "speed": 1.0,
                "performance_instructions": "Conversational, curious, restrained.",
                "generated_at": "2026-08-11T00:00:00Z",
                "generation_mode": "full-script",
                "take_count": 2,
                "selected_take": 1,
                "auditioned_without_music": True,
                "raw_audio": {"path": "audio/voice-raw.m4a", "sha256": sha256_file(raw_voice)},
                "clean_audio": {"path": "audio/voice-clean.m4a", "sha256": sha256_file(clean_voice)},
                "human_approved": True,
            }
        )
        write_json(self.project / "audio" / "voice-provenance.json", voice)
        shot_plan["captions"]["waveform_sha256"] = voice["clean_audio"]["sha256"]
        shot_plan["captions"]["timing_manually_corrected"] = True
        shot_plan["captions"]["phone_sound_qa"] = True
        shot_plan["captions"]["phone_muted_qa"] = True
        write_json(self.project / "shot-plan.json", shot_plan)

        manifest = read_json(self.project / "asset-manifest.json")
        manifest["audio_render"]["approved_tracks"] = ["voice-clean"]
        manifest["audio_render"]["ffprobe_verified"] = True
        manifest["audio_render"]["filter_graph_reviewed"] = True
        for asset in manifest["assets"]:
            is_source = asset["kind"] == "third-party-source"
            asset["rights_status"] = "human-approved" if is_source else "authorized"
            asset["privacy_status"] = "not-applicable" if is_source else "approved"
            asset["human_approved"] = True
            asset["sha256"] = "0" * 64
            asset["audio_policy"] = "discard"
            asset["audio_handling"]["input_audio_removed"] = True
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
                asset["capture_mode"] = "continuous-master"
                asset["capture_transport"] = "browser-screencast"
                asset["timeline_progression_verified"] = True
                asset["dynamic_frames_verified"] = True
                asset["authenticated_session_verified"] = True
        write_json(self.project / "asset-manifest.json", manifest)
        set_research_evidence(self.project, "00:00:00-00:00:01")

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
        research_path = self.project / "research.md"
        research_path.write_text(
            research_path.read_text(encoding="utf-8").replace(
                "| C1 | SOURCE_QUOTE | 00:00:00-00:00:01 |",
                "| C1 | SOURCE_QUOTE | Introduction, paragraph 4 |",
            ),
            encoding="utf-8",
        )
        result = self.validate(release_ready=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_missing_authenticated_browser_requires_exact_blocker(self) -> None:
        state = read_json(self.project / "project-state.json")
        state["status"] = "blocked"
        state["stage"] = "linko-capture-approval"
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

    def test_empty_evidence_ledger_row_blocks_release(self) -> None:
        self.make_release_ready()
        research_path = self.project / "research.md"
        research_path.write_text(
            research_path.read_text(encoding="utf-8").replace(
                "| C1 | SOURCE_QUOTE | 00:00:00-00:00:01 | Example verified statement. | Example script language. | verified |",
                "| C1 | SOURCE_QUOTE | | | | pending |",
            ),
            encoding="utf-8",
        )
        result = self.validate(release_ready=True)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn('"release_asset:primary-source:evidence_ledger:C1"', result.stdout)

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

    def test_duplicate_source_window_blocks_release(self) -> None:
        self.make_release_ready()
        shot_plan = read_json(self.project / "shot-plan.json")
        shot_plan["shots"][1]["asset_id"] = shot_plan["shots"][0]["asset_id"]
        shot_plan["shots"][1]["source_start_seconds"] = shot_plan["shots"][0]["source_start_seconds"]
        shot_plan["shots"][1]["source_end_seconds"] = shot_plan["shots"][0]["source_end_seconds"]
        write_json(self.project / "shot-plan.json", shot_plan)
        result = self.validate(release_ready=True)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn('"unique_source_windows"', result.stdout)

    def test_stale_caption_waveform_blocks_release(self) -> None:
        self.make_release_ready()
        shot_plan = read_json(self.project / "shot-plan.json")
        shot_plan["captions"]["waveform_sha256"] = "f" * 64
        write_json(self.project / "shot-plan.json", shot_plan)
        result = self.validate(release_ready=True)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn('"captions:waveform_binding"', result.stdout)

    def test_incomplete_linko_master_capture_blocks_release(self) -> None:
        self.make_release_ready()
        manifest = read_json(self.project / "asset-manifest.json")
        manifest["assets"][1]["capture_steps"].pop()
        write_json(self.project / "asset-manifest.json", manifest)
        result = self.validate(release_ready=True)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn('"authenticated_continuous_linko_capture"', result.stdout)

    def test_unreviewed_intentional_source_audio_blocks_release(self) -> None:
        self.make_release_ready()
        manifest = read_json(self.project / "asset-manifest.json")
        source = manifest["assets"][0]
        source["audio_policy"] = "intentional"
        source["audio_handling"]["input_audio_removed"] = False
        source["audio_handling"]["approved_mix_track"] = "source-dialogue"
        source["audio_handling"]["loudness_reviewed"] = False
        source["audio_handling"]["transition_reviewed"] = True
        write_json(self.project / "asset-manifest.json", manifest)
        result = self.validate(release_ready=True)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn('"release_asset:primary-source:loudness_reviewed"', result.stdout)


if __name__ == "__main__":
    unittest.main()
