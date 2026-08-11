# Production and audio

## Project layout

```text
project/
├── short-brief.md
├── project-state.json
├── research.md
├── script.md
├── shot-plan.json
├── asset-manifest.json
├── publish-copy.md
├── release-checklist.md
├── assets/{source,linko,licensed}/
├── audio/
│   └── voice-provenance.json
├── render/
└── qa/
```

Keep downloaded sources, approved excerpts, narration, renders, and QA artifacts separate. Never store credentials, cookies, OAuth state, personal exports, or private notes.

## Timing skeleton

| Segment | Typical time | Function |
|---|---:|---|
| Personal setup and hook | 0–7s | Establish source and direct question |
| Source moment | 7–12s | Provide visible evidence; original audio is optional |
| Context and concrete example | 12–36s | Explain the necessary concept |
| Creator judgment | 36–48s | Land the opinion or distinction |
| Linko research trail | final 8–12s | Save, connect, or revisit the idea |
| Phase-out | final 3–5s | Reusable truthful CTA |

## Narration

- Keep speed, full performance instructions, take strategy, selected take, raw/clean paths and SHA-256 values, and all post-processing in `audio/voice-provenance.json`.
- When no source audio is inserted, prefer two or three complete takes and audition them without music.
- Split generation only for source-audio insertion, provider limits, or an explicit performance need.
- Preserve breaths and varied sentence endings.
- Record or generate at 48 kHz when supported.
- Time the edit and captions to the approved waveform rather than stretching speech to a fixed timeline.
- Regenerate pacing problems before considering time-stretching.
- For VO-only projects, discard external video audio at ingest and explicitly map only approved tracks.
- When source audio is intentional, mark it in the manifest, match perceived loudness, and approve J-cuts or crossfades.
- Keep the first rough cut free of music unless the brief explicitly requires it.

Avoid heavy compression that removes all human variation. Do not disguise a generated review voice as a human recording.

## Picture and captions

Default delivery:

- 1080×1920;
- project-native 24, 25, or 30 fps, locked after source preflight;
- H.264 video;
- AAC audio at 48 kHz.

Parameterize these values when the platform differs. Keep important text inside approximately 7% horizontal margins and away from lower platform controls. Use four to seven words per semantic phrase by default and two to five for hooks or emphasis; prefer one line and cap at two. Prefer the lower third over source footage and upper third over Linko UI. Inspect the first, middle, and final frame of every caption event. Hand-correct line breaks and timing rather than shrinking the system. A new approved waveform invalidates all prior caption timings.

## Source-shot approval

Record `source_start_seconds`, `source_end_seconds`, `visual_role`, `unique_source_shot_id`, and `audio_policy` for every motion shot. Confirm player time progression and pixel change across the first, middle, and final frames. Before rough cut, review a contact sheet and timecode table. Alternate crops of the same raw time window remain one source shot.

Also record decoded and active-picture dimensions, effective portrait crop pixels, upscale ratio, source/capture/output fps, capture transport, burned-text status, and a 100% crop. Prefer subject-aware crops for close shots and clean same-shot edge extension for wide shots. Reject unsafe center crops, stretching, player UI, black edges, screenshot-sequence motion, and periodic duplicate cadence.

For narration, record word count, target and measured duration/WPM, transcript hash and WER, pronunciation review, pause brief, long-pause count, and the locked selected-take hash. Reject content drift before tone review. Express demographic direction only through audible performance traits.

## Main cuts and cutdowns

Treat 15- and 30-second cutdowns as separate scripts with separate approval. Do not truncate the main version. Use the approved waveform and readable product actions to determine the main runtime instead of compressing narration or Linko actions to an integer duration.
