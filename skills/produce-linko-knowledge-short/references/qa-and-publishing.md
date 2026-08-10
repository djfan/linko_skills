# QA and publishing

## State machine

Progress through:

`preflight → source-research → angle-approval → script-and-shot-plan → rights-and-privacy → linko-capture → voice-and-edit → automated-qa → phone-qa → publication-approval → published`

Use these status values:

- `draft`
- `blocked`
- `review-ready`
- `publish-approved`
- `published`

Never jump from a topic directly to media production. Record approvals and blockers in `project-state.json`.

## Automated QA defaults

`validate_short.py` defaults to:

- duration 40–75 seconds;
- 1080×1920;
- 30 fps within 0.1 fps;
- audio present;
- integrated loudness between -18 and -14 LUFS;
- true peak at or below -1.0 dBTP;
- no detected black segment of 0.30 seconds or longer;
- no detected silence below -45 dB for 0.90 seconds or longer.

`validate_project.py` checks state, shot timing, asset references, rights and privacy states, placeholders, authenticated Linko capture, CTA truth, and release approvals.

Automated success does not validate argument quality, caption readability, privacy content, legal rights, recording authenticity, voice naturalness, or taste.

## Human phone QA

Review the exact file on a phone with sound and muted. Verify:

- factual fidelity and attribution;
- the ablation test without Linko footage;
- pace and voice naturalness;
- caption size, wrapping, and safe areas;
- product-capture truthfulness and privacy;
- third-party excerpt rights;
- CTA and destination truthfulness.

## Review cut delivery

Report exact limitations. Use language such as:

> The final Linko section is a placeholder made from approved operation frames because an authenticated recording session was unavailable. It is not represented as a live recording and remains blocked for final release.

Include the file URL, duration, dimensions, frame rate, loudness, voice provenance, source provenance, and manual decisions still open.

## Publication

Require explicit approval for the exact file, destination, metadata, excerpts, rights basis, privacy review, and disclosures. Re-verify after any metadata rewrite or transcode.

For services that reject MP4 metadata, create a separate upload copy, strip nonessential tags, and confirm duration, codecs, dimensions, and audio before upload.

Capture the upload response, artifact hash, and post or event identifier. A local file or attempted command is not publication evidence.
