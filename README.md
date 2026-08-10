# Linko Skills

Reusable Codex skills for turning Linko research into publishable knowledge content.

## Included skill

### `produce-linko-knowledge-short`

Creates, revises, validates, and prepares publication of evidence-led knowledge Shorts built from interviews, videos, podcasts, articles, books, and Linko notes. The default profile is an English YouTube Short, but language, platform, duration, format, and CTA are project inputs.

The workflow is knowledge-first:

1. verify the primary source at transcript or line level;
2. separate source claims from the creator's interpretation;
3. choose one opinionated, supportable thesis;
4. write a conversational micro-essay;
5. use real motion footage and an authorized Linko research trail;
6. render a review cut and run deterministic media QA;
7. keep privacy, rights, authenticity, and publication behind human approval gates.

Linko appears naturally near the end as the place where an idea is saved and connected. It is not treated as a feature-list product demo.

## Repository layout

```text
skills/
└── produce-linko-knowledge-short/
    ├── SKILL.md
    ├── agents/openai.yaml
    ├── assets/
    ├── references/
    └── scripts/
```

The repository README is intentionally outside the Skill folder. The Skill itself contains only runtime instructions and reusable resources.

## Install

Use the Codex Skill Installer:

```bash
python3 ~/.codex/skills/.system/skill-installer/scripts/install-skill-from-github.py \
  --repo djfan/linko_skills \
  --path skills/produce-linko-knowledge-short
```

The Skill becomes available on the next Codex turn. If the repository is private, the installer uses existing GitHub credentials or `GITHUB_TOKEN` / `GH_TOKEN`.

## Example prompts

```text
Use $produce-linko-knowledge-short to analyze this interview and propose the three strongest Short angles before writing anything.
```

```text
Use $produce-linko-knowledge-short to turn this video and my Linko notes into a 45–60 second English YouTube Short. Stop after the script and shot plan.
```

```text
Use $produce-linko-knowledge-short to diagnose this review cut, revise it, run technical QA, and prepare a human approval checklist. Do not publish it.
```

## Project initialization

From the Skill directory:

```bash
python3 scripts/init_short_project.py /path/to/new-short
```

This creates `project-state.json`, a brief, research ledger, script, JSON shot plan, asset manifest, QA and publishing templates, release checklist, and clean asset/output folders.

## Output contract

Each project keeps predictable artifacts:

```text
short-brief.md
project-state.json
research.md
script.md
shot-plan.json
asset-manifest.json
render/draft.mp4
qa/contact-sheet.png
qa/qa-report.md
publish-copy.md
release-checklist.md
```

Projects move through `draft`, `blocked`, `review-ready`, `publish-approved`, and `published`. A missing authenticated Linko capture session must produce `blocked: authenticated-capture-unavailable`; screenshot animation can be a disclosed prototype but never a final recording.

## Technical QA

Requirements:

- Python 3.10+
- FFmpeg and FFprobe

Run:

```bash
python3 scripts/validate_short.py /path/to/final.mp4 \
  --report /path/to/qa/report.json \
  --contact-sheet /path/to/qa/contact-sheet.png

python3 scripts/validate_project.py /path/to/project
python3 scripts/validate_project.py /path/to/project --release-ready
```

The validator checks duration, portrait format, frame rate, audio presence, loudness, true peak, black frames, and long silence. It cannot approve factual accuracy, caption readability, privacy, rights, recording authenticity, or publication authority; those remain manual gates.

## Optional production tools

The Skill is tool-agnostic, but a full production run may use:

- Playwright for repeatable Linko demo capture;
- Computer Use for unfamiliar UI recovery;
- a user-approved TTS provider or human narration;
- FFmpeg or Remotion for rendering;
- a platform upload tool after explicit approval.

Linko authentication is host-managed. The Skill never performs OAuth setup, token refresh, or account changes.

At preflight, the Skill inspects the operations actually available. If an imported resource cannot be edited or deleted through current tools, the project records a manual cleanup checklist instead of assuming support.

## Safety and rights

- Use a dedicated demo account and synthetic or approved Linko data.
- Do not commit credentials, cookies, personal exports, private notes, or third-party source media.
- Record source owners, canonical URLs, excerpt timecodes, and the human-reviewed rights basis.
- Do not describe animated screenshots as live recordings.
- Do not clone or imitate an identifiable voice without authorization.
- Do not upload or publish without approval of the exact file and destination.

The workflow was distilled from a real Linko knowledge-Short production and includes no bundled interview footage, trailer clips, account data, or credentials.

## Troubleshooting

### `ffmpeg` or `ffprobe` is missing

Install FFmpeg with the package manager for your platform, then rerun `validate_short.py`.

### The Skill Installer reports a local Python certificate error

Retry the installation command with `--method git`. This uses the installer's supported git sparse-checkout path instead of the ZIP download path.

### Linko capture is blocked

Provide an authenticated demo browser session. Do not add OAuth or tokens to the project and do not relabel screenshot prototypes as live capture.

### Release validation rejects an asset

Open `asset-manifest.json` and resolve `rights_status`, `privacy_status`, `placeholder`, and `human_approved`. Pending or unknown third-party rights intentionally block release.

### The CTA fails validation

Remove viewer-facing Linko access claims or verify a public destination in `project-state.json`. `Follow for the next idea.` remains safe without a Linko URL.

### A Linko test import cannot be cleaned up automatically

Record the exact resource or note in `project-state.json.manual_cleanup` and complete it manually in the demo account.
