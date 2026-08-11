---
name: produce-linko-knowledge-short
description: Research, script, produce, revise, validate, and prepare human-approved publication of evidence-led knowledge Shorts built from interviews, videos, podcasts, articles, books, or Linko notes, with Linko appearing naturally as the creator's research trail rather than as a product demo. Use for Linko-related short-form source analysis, angle selection, conversational scripts, shot plans, asset and rights manifests, authenticated product capture, voice briefs, FFmpeg or Remotion edits, technical and phone QA, review cuts, publishing copy, and release handoff.
---

# Produce Linko Knowledge Short

Produce one complete, opinionated knowledge micro-essay and reveal Linko only where the creator saves or connects the idea. Keep research, attribution, privacy, rights, and release gates visible throughout production.

## Load the standards

Read the references needed for the requested stage:

- Always read [references/editorial-contract.md](references/editorial-contract.md).
- Read [references/evidence-and-rights.md](references/evidence-and-rights.md) before research, quotation, asset selection, or rights review.
- Read [references/linko-capture.md](references/linko-capture.md) before Linko operations or product capture.
- Read [references/production-and-audio.md](references/production-and-audio.md) before narration, editing, or rendering.
- Read [references/qa-and-publishing.md](references/qa-and-publishing.md) before validation, delivery, upload, or publication.

## Classify the requested stage

Determine the narrowest requested deliverable:

1. **Explore** — research the source and rank editorial angles.
2. **Script** — deliver the evidence boundary, English VO, and shot plan.
3. **Produce** — capture authorized assets, generate narration, and render a review cut.
4. **Revise** — diagnose the current cut against the editorial and technical gates before changing it.
5. **Release** — validate the exact final file and publish only with explicit approval.

Do not expand a script request into recording or publishing. Treat uploads, social posts, and account changes as separate external actions.

## Initialize a project

Run:

```bash
python3 scripts/init_short_project.py <project-directory>
```

This creates the input brief, state file, predictable output contracts, release checklist, and asset folders. Preserve raw sources separately from approved excerpts and renders.

## Honor the contract

Require or safely infer these inputs before media production:

- topic and primary source;
- audience, platform, target duration, and language;
- editorial and narrator voice;
- Linko resource, note, or connection to reveal;
- source URLs, timecodes or lines, and known rights state;
- CTA and publication destination when one exists.

If the user provides only a topic, stop after source research and two or three angles. Do not jump directly to a finished video.

Keep these outputs predictable:

- `research.md`
- `script.md`
- `shot-plan.json`
- `asset-manifest.json`
- `audio/voice-provenance.json`
- `render/draft.mp4`
- `qa/contact-sheet.png`
- `qa/report.json`
- `qa/qa-report.md`
- `publish-copy.md`

Track the stage and approvals in `project-state.json`. Use `draft`, `blocked`, `review-ready`, `publish-approved`, or `published` as status values. Move through script approval, voice audition, source-shot approval, Linko capture approval, rough cut, caption/phone QA, and release as separate checkpoints. Record `PASS`, `REVISE`, or `BLOCKED` plus evidence at every checkpoint. Never imply that `draft` is publishable.

## Execute the workflow

### 1. Preflight capabilities and define the audience promise

Check the actual Linko operations available, authenticated browser state, video tools, fonts or brand assets, and writable output path before promising a render. If resource cleanup cannot be automated, add a manual cleanup checklist rather than assuming edit or delete support.

Write one sentence completing: `After this Short, the viewer can explain...`.

Set one thesis, one target viewer, one platform, one language, one duration range, and one review destination. Default to a 45–60 second English YouTube Short only when the user has not specified another format.

### 2. Build the evidence boundary

Prefer the original audiovisual or textual source. Create timestamped or line-level notes and distinguish:

- exact source statements;
- interviewer or author claims;
- independently verified context;
- the creator's inference.

Record every claim in `research.md`. Give each evidence-bearing asset at least one ledger ID plus an exact timecode, page, line, or section locator in `asset-manifest.json`. Reject a strong hook when the source only supports a weaker statement of intent, possibility, or interpretation. Do not use platform AI summaries or search snippets as final quotation evidence.

### 3. Rank angles before scripting

Propose up to three distinct angles. Score each for:

- a clear tension or question;
- teachable context;
- a defensible original conclusion;
- visual support;
- fit within one Short.

Choose one. Move other ideas into future episodes instead of compressing them into the current script. Obtain editorial approval before expensive capture or rendering when the thesis materially changes the user's direction.

### 4. Write the spoken essay

Use this sequence as a guide, not a rigid formula:

`personal setup → direct question → source moment → plain-language context → concrete example → creator judgment → Linko trail → reusable outro`

Write short clauses and everyday verbs. Introduce only the specialist terms the argument needs and explain them immediately. Keep the creator VO continuous when the picture changes to Linko.

Pass the deletion test: removing the Linko footage and outro must leave a complete, useful argument.

### 5. Lock the editorial package and design the shot plan

Obtain approval of the central claim, tone, language, narrator brief, CTA truth, and approximate duration before expensive media work. If the usable source mode changes after script approval—for example, an evidence-bearing interview is removed and only trailer or B-roll remains—repeat the cold-read context test and evidence-boundary approval before proceeding.

Assign every sentence a visual purpose. For each motion shot, record the source time range, visual role, unique source-shot ID, and `audio_policy: discard | intentional`. Do not disguise one source window as several clips through alternate crops. Before rough cut, approve a contact sheet and timecode table that demonstrate enough independent source motion for the intended 2–4 second rhythm. Prefer real motion from the primary source, interview, licensed B-roll, or authorized product recording. Use trailer or cinematic footage as emotional support, not as the evidence-bearing core.

Place Linko in approximately the final 15–20% unless the story requires otherwise. Show a real save, note, connection, or related-resource action that explains why the idea is worth keeping. Avoid feature lists.

Use zooms only to direct attention. Do not animate a screenshot and call it a screen recording. A placeholder is allowed in a review cut only when labeled in the delivery and blocked from final release.

### 6. Capture safely

Use a dedicated Linko demo account and synthetic or approved content. Capture the product at a readable desktop size such as 1440×900, then crop and pan inside the 9:16 canvas. Hide notifications, unrelated notes, identifiers, and private recommendations.

Use deterministic browser automation for known flows and computer use only for exploration or recovery. Record one continuous master capture from source URL copy through Add Link, submit, Resource appearance, creation of a structured hierarchical Note beneath it, and Save or Publish. Allow editing to accelerate typing and network waits only. Validate timeline progression plus first/middle/final frame changes. Do not alter OAuth, tokens, or Linko authentication inside this skill. When final capture requires an unavailable authenticated session, set `status` to `blocked` and `blocker` to `authenticated-capture-unavailable`. A screenshot prototype may remain a disclosed draft but can never satisfy final capture.

### 7. Produce narration and audio continuity

Create a voice brief that describes age range, region, conversational intent, pace, energy, pronunciation, and negative directions. Do not clone or imitate an identifiable person's voice without authorization.

Record provider, model, voice ID, speed, full performance instructions, generation date, take strategy, selected take, raw and clean paths and hashes, and every post-process operation in `audio/voice-provenance.json`. When no source audio is intentionally inserted, prefer two or three complete takes, audition the narration alone, and regenerate poor pacing instead of time-stretching it. Split generation only for source-audio insertion, provider limits, or an explicit performance need. Approve the voice before rough cut.

Discard external video audio at ingest for VO-only projects and explicitly map only approved tracks at render. If source audio is intentional, mark it in the asset manifest and approve its loudness and transition treatment. Start the first rough cut without music unless the brief explicitly requires it.

### 8. Edit the review cut

Render portrait video at 1080×1920 and 30 fps unless the destination requires otherwise. Bind captions to the SHA-256 of the final approved narration waveform; any voice change invalidates the timings. Use semantic phrases of four to seven words by default, with two to five words for hooks or emphasis. Prefer one line and allow at most two. Place captions in the lower third over source footage and the upper third over Linko UI when needed for readability. Hand-correct line breaks and timing, then inspect the exact cut on a phone with sound and muted.

Keep the final Linko action readable for several seconds. Default to the structured CTA type `generic` and copy such as `Follow for the next idea.` Classify any viewer-facing Linko access claim as `public-linko`, regardless of its wording, and use it only after verifying the exact public destination in both `project-state.json` and `publish-copy.md`.

Treat 15- or 30-second cutdowns as separate editorial deliverables with their own approved scripts and pacing. Do not publish a truncation of the main cut. Let the approved waveform and readable Linko actions determine the main version's duration; do not speed up speech or product actions merely to hit an integer runtime.

### 9. Run technical and editorial QA

Run:

```bash
python3 scripts/validate_short.py render/final.mp4 \
  --report qa/report.json \
  --contact-sheet qa/contact-sheet.png

python3 scripts/validate_project.py .
```

Treat script success as technical evidence only. Inspect the contact sheet and complete the manual gates in `release-checklist.md`: thesis clarity, factual attribution, real-motion provenance, Linko authenticity, privacy, rights, voice disclosure, caption readability, and CTA truthfulness.

### 10. Release with evidence

Run `python3 scripts/validate_project.py . --release-ready` before publication. It must bind a passing `qa/report.json` to the exact final path, SHA-256, and independently probed media parameters. Publish only when the user explicitly approves the exact cut and destination. Strip nonessential media metadata when the destination rejects it, then re-run media integrity checks. Report:

- the final URL or artifact path;
- duration, dimensions, frame rate, loudness, and hash when available;
- source and voice provenance;
- known limitations;
- the publication event or receipt.

Never claim upload or publication without a successful service response.

## Stop conditions

Stop and ask for the smallest missing decision when:

- the source cannot support the chosen claim;
- the intended Linko action requires an unavailable authenticated session;
- private or unrelated account data is visible;
- a third-party excerpt lacks a reviewable rights basis;
- a requested voice would imitate a real person without authorization;
- the user has not approved an external upload or publication.

## Bundled resources

- `scripts/init_short_project.py` — create a clean production workspace from the bundled templates.
- `scripts/validate_short.py` — inspect media, measure loudness, detect long silence and black frames, and generate a contact sheet plus JSON report.
- `scripts/validate_project.py` — validate state, shots, asset provenance, Linko capture authenticity, CTA truth, and release approvals.
- `assets/*.template.*` — reusable state, brief, research, script, shot, asset, QA, publishing, and release files.
- `references/` — stage-specific editorial, evidence, Linko capture, production, QA, and publishing guidance.
