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
├── render/
└── qa/
```

Keep downloaded sources, approved excerpts, narration, renders, and QA artifacts separate. Never store credentials, cookies, OAuth state, personal exports, or private notes.

## Timing skeleton

| Segment | Typical time | Function |
|---|---:|---|
| Personal setup and hook | 0–7s | Establish source and direct question |
| Source clip | 7–12s | Provide visible evidence and original audio |
| Context and concrete example | 12–36s | Explain the necessary concept |
| Creator judgment | 36–48s | Land the opinion or distinction |
| Linko research trail | final 8–12s | Save, connect, or revisit the idea |
| Phase-out | final 3–5s | Reusable truthful CTA |

## Narration

- Keep text, pronunciations, provider, voice identifier, model, and generation date with the project.
- Generate or record two restrained takes when voice style matters.
- Preserve breaths and varied sentence endings.
- Record or generate at 48 kHz when supported.
- Time the edit to the approved waveform rather than stretching speech to a fixed timeline.
- Match narrator and source-clip perceived loudness before music.
- Use 150–250 ms fades and one quiet room-tone or music bed across source transitions.

Avoid heavy compression that removes all human variation. Do not disguise a generated review voice as a human recording.

## Picture and captions

Default delivery:

- 1080×1920;
- 30 fps;
- H.264 video;
- AAC audio at 48 kHz.

Parameterize these values when the platform differs. Keep important text inside approximately 7% horizontal margins and away from lower platform controls. Inspect the first, middle, and final frame of every caption event. Break long captions into semantic units rather than shrinking the entire system.
