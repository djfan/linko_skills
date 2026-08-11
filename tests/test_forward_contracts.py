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
    (project / "qa" / "cover.png").write_bytes(b"cover proof")
    (project / "publish-copy.md").write_text(
        "---\n"
        f"cta_type: {cta_type}\n"
        f"cta_destination: {destination}\n"
        "primary_title: Primary title\n"
        "title_variant_a: Variant A\n"
        "title_variant_b: Variant B\n"
        "language: en\n"
        "category: Education\n"
        "audience: not-made-for-kids\n"
        "paid_promotion_decision: none\n"
        "remixing_decision: allowed\n"
        "related_video: none\n"
        "visibility: unlisted\n"
        "cover_timestamp: 00:00:00.5\n"
        "cover_proof_path: qa/cover.png\n"
        "policy_verified_at: 2026-08-11\n"
        "description_ready: yes\n"
        "hashtags: '#knowledge #history'\n"
        "studio_tags: knowledge,history\n"
        "source_attribution_ready: yes\n"
        "synthetic_altered_content_decision: disclosed-voice\n"
        "pinned_comment: What would you save?\n"
        "audience_question: What changed your interpretation?\n"
        "platform_link_behavior: description-link\n"
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
            "testsrc2=s=1080x1920:r=30:d=1",
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
        state["delivery_fps"] = 30
        state["cadence"]["source_native_verified"] = True
        state["editorial_review"]["cold_read_context_passed"] = True
        state["editorial_review"]["evidence_boundary_approved"] = True
        state["editorial_review"]["first_person_premise_verified"] = True
        state["editorial_review"]["saved_object"] = "official trailer"
        state["ui_geometry_signature"] = "linko-panel-v1"
        state["cta"]["type"] = "generic"
        state["cta"]["text"] = "What would you save?"
        for key in state["approvals"]:
            state["approvals"][key] = True
        write_json(self.project / "project-state.json", state)
        write_publish_copy(self.project, "generic", "", "What would you save?")

        shot_plan = read_json(self.project / "shot-plan.json")
        shot_plan["format"]["delivery_fps"] = 30
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
            shot["motion_validation"]["continuous_motion_source"] = True
            shot["motion_validation"]["screenshot_sequence"] = False
            shot["motion_validation"]["frame_count"] = 15
            shot["motion_validation"]["adjacent_exact_duplicates"] = 0
            shot["motion_validation"]["max_duplicate_run"] = 0
            shot["motion_validation"]["periodic_duplicates_detected"] = False
            shot["source_media"] = {
                "decoded_width": 1920,
                "decoded_height": 1080,
                "source_fps": 30,
                "capture_fps": 30,
                "active_width": 1920,
                "active_height": 1080,
                "crop_width": 608,
                "crop_height": 1080,
                "upscale_ratio": 1.78,
                "capture_transport": "source-file" if shot["asset_id"] == "primary-source" else "browser-screencast",
            }
            shot["reframe_strategy"] = "subject-aware-crop"
            shot["subject_safe_space_reviewed"] = True
            shot["burned_text_status"] = "none"
            shot["player_ui_absent"] = True
            shot["black_edges_absent"] = True
            shot["not_stretched"] = True
            crop_path = self.project / "qa" / f"{shot['id']}-crop.png"
            crop_path.write_bytes(b"crop proof")
            shot["crop_100_percent_evidence"] = f"qa/{shot['id']}-crop.png"
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
                "script_word_count": 135,
                "target_duration_seconds": 60,
                "target_wpm": {"min": 130, "max": 145},
                "actual_duration_seconds": 60,
                "actual_wpm": 135,
                "pause_brief": "Pause after the hook and before the saved question.",
                "long_pause_count": 2,
                "audition_decision": "PASS",
                "audible_traits_only": True,
                "auditioned_without_music": True,
                "raw_audio": {"path": "audio/voice-raw.m4a", "sha256": sha256_file(raw_voice)},
                "clean_audio": {"path": "audio/voice-clean.m4a", "sha256": sha256_file(clean_voice)},
                "human_approved": True,
            }
        )
        voice["selected_take_locked_sha256"] = voice["clean_audio"]["sha256"]
        transcript_path = self.project / "audio" / "voice-transcript.txt"
        transcript_path.write_text("Example narration transcript.\n", encoding="utf-8")
        voice["transcript"] = {"path": "audio/voice-transcript.txt", "sha256": sha256_file(transcript_path), "wer": 0.0}
        voice["pronunciation_checklist"] = [{"term": "Linko", "status": "approved"}]
        write_json(self.project / "audio" / "voice-provenance.json", voice)
        shot_plan["captions"]["waveform_sha256"] = voice["clean_audio"]["sha256"]
        shot_plan["captions"]["timing_manually_corrected"] = True
        shot_plan["captions"]["phone_sound_qa"] = True
        shot_plan["captions"]["phone_muted_qa"] = True
        alignment_path = self.project / "qa" / "word-alignment.json"
        alignment_path.write_text("{}\n", encoding="utf-8")
        shot_plan["captions"]["alignment"] = {"path": "qa/word-alignment.json", "sha256": sha256_file(alignment_path)}
        shot_plan["captions"]["event_count"] = 1
        shot_plan["captions"]["style"] = {"font": "Inter", "size_px": 64, "position_policy": "source-lower-linko-upper"}
        shot_plan["captions"]["highlight_count"] = 1
        shot_plan["captions"]["collision_review"]["burned_source_text_reviewed"] = True
        shot_plan["captions"]["collision_review"]["platform_controls_reviewed"] = True
        for frame in ("first_frame", "middle_frame", "final_frame"):
            frame_path = self.project / "qa" / f"caption-{frame}.png"
            frame_path.write_bytes(b"caption frame")
            shot_plan["captions"]["collision_review"][frame] = f"qa/caption-{frame}.png"
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
                for field in ("raw_master", "edited_cut", "edit_decision_list"):
                    suffix = "md" if field == "edit_decision_list" else "mp4"
                    artifact = self.project / "assets" / "linko" / f"{field}.{suffix}"
                    artifact.write_bytes(field.encode())
                    asset[field] = {"path": f"assets/linko/{field}.{suffix}", "sha256": sha256_file(artifact)}
                for key in asset["transition_integrity"]:
                    asset["transition_integrity"][key] = True
                asset["semantic_qa"].update({
                    "saved_object": "official trailer",
                    "note_title_readable": True,
                    "requested_hierarchy_readable": True,
                    "open_question_readable": True,
                    "no_post_production_tag_overlay": True,
                })
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
            "--fps",
            "30",
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

        state = read_json(self.project / "project-state.json")
        dependency_values = {
            "script_sha256": sha256_file(self.project / "script.md"),
            "voice_sha256": voice["clean_audio"]["sha256"],
            "delivery_fps": 30,
            "ui_geometry_signature": state["ui_geometry_signature"],
            "final_sha256": sha256_file(final_video),
        }
        dependency_fields = {
            "voice_audition": ("script_sha256",),
            "source_shot_approval": ("delivery_fps",),
            "linko_capture_approval": ("delivery_fps", "ui_geometry_signature"),
            "rough_cut": ("script_sha256", "voice_sha256", "delivery_fps"),
            "caption_phone_qa": ("voice_sha256", "delivery_fps"),
            "release": ("final_sha256",),
        }
        for name, checkpoint in state["checkpoints"].items():
            artifact = self.project / "qa" / f"{name}.bin"
            artifact.write_bytes(name.encode())
            checkpoint.update({
                "result": "PASS",
                "scope": "final-asset" if name in {"caption_phone_qa", "release"} else "candidate-asset",
                "artifact_path": f"qa/{name}.bin",
                "sha256": sha256_file(artifact),
                "approved_for": "release",
                "dependency_lock": {field: dependency_values[field] for field in dependency_fields.get(name, ())},
            })
        for name, proof in state["risk_proofs"].items():
            if name == "authored_bridge":
                continue
            artifact = self.project / "qa" / f"proof-{name}.bin"
            artifact.write_bytes(name.encode())
            proof.update({"result": "PASS", "artifact_path": f"qa/proof-{name}.bin", "sha256": sha256_file(artifact)})
        write_json(self.project / "project-state.json", state)

    def validate(self, release_ready: bool = False) -> subprocess.CompletedProcess[str]:
        arguments = [sys.executable, str(VALIDATE), str(self.project)]
        if release_ready:
            arguments.append("--release-ready")
        return run(*arguments)

    def add_valid_bridge(self) -> None:
        bridge_path = self.project / "assets" / "licensed" / "bridge.mp4"
        bridge_path.write_bytes(b"authored bridge")
        proof_path = self.project / "qa" / "bridge-overlay.png"
        proof_path.write_bytes(b"overlay")
        manifest = read_json(self.project / "asset-manifest.json")
        manifest["assets"].append(
            {
                "id": "authored-bridge",
                "kind": "authored-bridge",
                "asset_type": "authored-bridge",
                "owner": "creator",
                "canonical_url": None,
                "local_path": "assets/licensed/bridge.mp4",
                "purpose": "communicate transfer intent",
                "audio_policy": "discard",
                "audio_handling": {"input_audio_removed": True, "approved_mix_track": None, "loudness_reviewed": False, "transition_reviewed": False},
                "rights_status": "owned",
                "rights_basis": "creator-authored animation",
                "privacy_status": "not-applicable",
                "sha256": sha256_file(bridge_path),
                "placeholder": False,
                "human_approved": True,
                "claims_product_success": False,
                "ends_before_real_action": True,
                "match_cut": {
                    "real_asset_id": "linko-capture",
                    "fps_match": True,
                    "geometry_match": True,
                    "text_match": True,
                    "url_state_match": True,
                    "button_state_match": True,
                    "proof": {"path": "qa/bridge-overlay.png", "sha256": sha256_file(proof_path)},
                },
            }
        )
        write_json(self.project / "asset-manifest.json", manifest)
        state = read_json(self.project / "project-state.json")
        state["risk_proofs"]["authored_bridge"] = {"required": True, "result": "PASS", "artifact_path": "qa/bridge-overlay.png", "sha256": sha256_file(proof_path)}
        write_json(self.project / "project-state.json", state)

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

    def test_native_24_fps_passes_and_24_to_30_cadence_fails(self) -> None:
        native = Path(self.temporary.name) / "native24.mp4"
        damaged = Path(self.temporary.name) / "damaged30.mp4"
        create = run(
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-f", "lavfi", "-i", "testsrc2=s=1080x1920:r=24:d=1",
            "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000:duration=1",
            "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-shortest", str(native),
        )
        self.assertEqual(create.returncode, 0, create.stderr)
        convert = run(
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(native),
            "-vf", "fps=30", "-c:v", "libx264", "-preset", "ultrafast", "-qp", "0", "-c:a", "copy", str(damaged),
        )
        self.assertEqual(convert.returncode, 0, convert.stderr)
        common = ("--min-duration", "0.5", "--max-duration", "2", "--min-lufs", "-40", "--max-lufs", "0", "--max-true-peak", "0")
        native_result = run(sys.executable, str(VALIDATE_SHORT), str(native), "--fps", "24", *common)
        self.assertEqual(native_result.returncode, 0, native_result.stdout + native_result.stderr)
        damaged_result = run(sys.executable, str(VALIDATE_SHORT), str(damaged), "--fps", "30", *common)
        self.assertEqual(damaged_result.returncode, 1, damaged_result.stdout + damaged_result.stderr)
        self.assertIn('"periodic_duplicate_cadence"', damaged_result.stdout)

    def test_method_checkpoint_cannot_approve_release_asset(self) -> None:
        self.make_release_ready()
        state = read_json(self.project / "project-state.json")
        state["checkpoints"]["linko_capture_approval"]["scope"] = "method"
        state["checkpoints"]["linko_capture_approval"]["approved_for"] = "experimentation"
        write_json(self.project / "project-state.json", state)
        result = self.validate(release_ready=True)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn('"checkpoint:linko_capture_approval:scope"', result.stdout)

    def test_screenshot_sequence_motion_blocks_release(self) -> None:
        self.make_release_ready()
        shot_plan = read_json(self.project / "shot-plan.json")
        shot_plan["shots"][0]["motion_validation"]["screenshot_sequence"] = True
        shot_plan["shots"][0]["motion_validation"]["continuous_motion_source"] = False
        write_json(self.project / "shot-plan.json", shot_plan)
        result = self.validate(release_ready=True)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn('"release_shot:0:not_screenshot_sequence"', result.stdout)

    def test_authored_bridge_cannot_replace_authenticated_linko_capture(self) -> None:
        self.make_release_ready()
        self.add_valid_bridge()
        manifest = read_json(self.project / "asset-manifest.json")
        manifest["assets"] = [asset for asset in manifest["assets"] if asset["id"] != "linko-capture"]
        write_json(self.project / "asset-manifest.json", manifest)
        shot_plan = read_json(self.project / "shot-plan.json")
        shot_plan["shots"][1]["asset_id"] = "authored-bridge"
        write_json(self.project / "shot-plan.json", shot_plan)
        result = self.validate(release_ready=True)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn('"authenticated_continuous_linko_capture"', result.stdout)

    def test_fake_success_or_mismatched_bridge_blocks_release(self) -> None:
        self.make_release_ready()
        self.add_valid_bridge()
        manifest = read_json(self.project / "asset-manifest.json")
        bridge = manifest["assets"][-1]
        bridge["claims_product_success"] = True
        bridge["match_cut"]["geometry_match"] = False
        write_json(self.project / "asset-manifest.json", manifest)
        result = self.validate(release_ready=True)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn('"bridge:authored-bridge:truth_boundary"', result.stdout)
        self.assertIn('"bridge:authored-bridge:geometry_match"', result.stdout)

    def test_resource_tag_cannot_satisfy_requested_note_tag(self) -> None:
        self.make_release_ready()
        manifest = read_json(self.project / "asset-manifest.json")
        semantic = manifest["assets"][1]["semantic_qa"]
        semantic["requested_note_tag"] = "Film"
        semantic["note_tag_owner_verified_in_ui"] = False
        write_json(self.project / "asset-manifest.json", manifest)
        result = self.validate(release_ready=True)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn('"linko:linko-capture:note_tag_owner"', result.stdout)

    def test_post_lock_candidate_requires_renewed_exact_file_qa(self) -> None:
        self.make_release_ready()
        state = read_json(self.project / "project-state.json")
        revision = state["post_lock_revision"]
        revision["active"] = True
        for field in ("prior_canonical", "scoped_proof", "full_candidate"):
            artifact = self.project / "render" / f"{field}.mp4"
            artifact.write_bytes(field.encode())
            revision[field] = {"path": f"render/{field}.mp4", "sha256": sha256_file(artifact)}
        revision["changed_region"] = "00:00:00.5-00:00:01.0"
        revision["continuity_boundaries_reviewed"] = True
        revision["unchanged_streams_or_ranges_verified"] = True
        revision["candidate_passed"] = True
        revision["canonical_replaced"] = True
        revision["exact_file_qa_renewed"] = False
        write_json(self.project / "project-state.json", state)
        result = self.validate(release_ready=True)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn('"post_lock:exact_file_qa_renewed"', result.stdout)

    def test_voice_drift_or_missing_pronunciation_blocks_release(self) -> None:
        for failure in ("wer", "pronunciation"):
            with self.subTest(failure=failure):
                self.make_release_ready()
                voice = read_json(self.project / "audio" / "voice-provenance.json")
                if failure == "wer":
                    voice["transcript"]["wer"] = 0.1
                else:
                    voice["pronunciation_checklist"] = []
                write_json(self.project / "audio" / "voice-provenance.json", voice)
                result = self.validate(release_ready=True)
                self.assertEqual(result.returncode, 1, result.stdout + result.stderr)

    def test_complete_publishing_package_is_release_only(self) -> None:
        draft_result = self.validate()
        self.assertEqual(draft_result.returncode, 0, draft_result.stdout + draft_result.stderr)
        self.make_release_ready()
        publish = self.project / "publish-copy.md"
        publish.write_text(publish.read_text(encoding="utf-8").replace("primary_title: Primary title", "primary_title:"), encoding="utf-8")
        release_result = self.validate(release_ready=True)
        self.assertEqual(release_result.returncode, 1, release_result.stdout + release_result.stderr)
        self.assertIn('"publishing:primary_title"', release_result.stdout)


if __name__ == "__main__":
    unittest.main()
