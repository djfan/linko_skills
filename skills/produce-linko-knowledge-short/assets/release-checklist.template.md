# Release checklist

## Editorial

- [ ] One thesis is clear and memorable.
- [ ] The Short remains complete without the Linko ending.
- [ ] Source statements and creator inference are distinguishable.
- [ ] The script uses conversational language and provides necessary context.
- [ ] A source-mode change triggered a new cold-read and evidence-boundary review.
- [ ] A cutdown, if any, has its own approved script and pacing.

## Visual and audio

- [ ] Opening and source footage are real motion, not disguised screenshots.
- [ ] Linko footage is a real authorized recording or clearly labeled review placeholder.
- [ ] Captions are readable on a phone and do not collide with source subtitles or platform UI.
- [ ] Voice provenance is recorded and any generated review voice is disclosed.
- [ ] The approved voice take was auditioned without music before rough cut.
- [ ] Motion shots have unique source windows plus timeline and frame-change evidence.
- [ ] VO-only inputs have source audio discarded; intentional source audio has approved loudness and transitions.
- [ ] Captions are bound to the approved waveform and were checked with sound and muted.

## Privacy and rights

- [ ] Linko capture shows only demo or approved data.
- [ ] Linko is one continuous URL → Add Link → Resource → structured Note → Save/Publish master capture.
- [ ] Notifications, identifiers, and unrelated notes are absent.
- [ ] Every third-party excerpt has owner, URL, timecode/page/line/section, linked evidence IDs, and a human-reviewed rights basis.
- [ ] The outro promises only a destination or action that exists.

## Technical QA

- [ ] `validate_short.py` passes and `qa/report.json` matches the exact final path and SHA-256.
- [ ] Contact sheet and targeted caption frames were visually inspected.
- [ ] Final upload copy was rechecked after metadata changes or transcoding.

## Release authority

- [ ] The human approved this exact file.
- [ ] The human approved the destination and publication action.
- [ ] `project-state.json` status is `publish-approved`.
- [ ] `validate_project.py . --release-ready` passes.
- [ ] Upload response, hash, and post/event identifier are recorded.

## Review notes

- Approved file:
- SHA-256:
- Destination:
- Approver:
- Known limitations:
- Upload/post receipt:
