#!/usr/bin/env python3
"""Contract tests for five representative Linko Short production scenarios."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
SKILL = REPO / "skills" / "produce-linko-knowledge-short"
INIT = SKILL / "scripts" / "init_short_project.py"
VALIDATE = SKILL / "scripts" / "validate_project.py"


def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, check=False, capture_output=True, text=True)


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


class ForwardContractTests(unittest.TestCase):
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

        manifest = read_json(self.project / "asset-manifest.json")
        for asset in manifest["assets"]:
            asset["rights_status"] = "human-approved" if asset["kind"] == "third-party-source" else "authorized"
            asset["privacy_status"] = "not-applicable" if asset["kind"] == "third-party-source" else "approved"
            asset["human_approved"] = True
            asset["sha256"] = "0" * 64
            if asset["kind"] == "third-party-source":
                asset["owner"] = "Example publisher"
                asset["canonical_url"] = "https://example.com/source"
            if asset["kind"] == "linko-capture":
                asset["capture_mode"] = "live"
                asset["authenticated_session_verified"] = True
        write_json(self.project / "asset-manifest.json", manifest)
        (self.project / "render" / "final.mp4").touch()

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
        manifest["assets"][0]["kind"] = "third-party-article"
        manifest["assets"][0]["excerpt_start_seconds"] = None
        manifest["assets"][0]["excerpt_end_seconds"] = None
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

    def test_unverified_public_linko_cta_blocks_release(self) -> None:
        self.make_release_ready()
        (self.project / "publish-copy.md").write_text(
            "# Publish copy\n\nFull notes in Linko.\n", encoding="utf-8"
        )
        result = self.validate(release_ready=True)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn('"public_cta_verified"', result.stdout)


if __name__ == "__main__":
    unittest.main()
