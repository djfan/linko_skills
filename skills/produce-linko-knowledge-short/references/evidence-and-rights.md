# Evidence and rights

## Evidence hierarchy

Use sources in this order:

1. Original video, audio, transcript, paper, article, book, or official publication.
2. Authoritative scholarship or documentation for necessary context.
3. Reputable secondary reporting for navigation or corroboration.
4. Platform summaries, OCR, ASR, or AI answers for discovery only.

Verify quotations against the original. Save timecodes or line references. When subtitles are burned into a video, inspect the frames and audio rather than treating OCR as conclusive.

## Evidence labels

Mark each planned line in `research.md` as one of:

- `SOURCE_QUOTE`
- `SOURCE_PARAPHRASE`
- `VERIFIED_CONTEXT`
- `CREATOR_INFERENCE`

Use epistemically accurate verbs. `Says`, `suggests`, `does not mean to`, `may`, and `can be read as` are not interchangeable. Record rejected or narrowed claims so they do not return during editing.

## Asset manifest

Record every visual, audio, font, and product-capture asset in `asset-manifest.json` with:

- owner and canonical URL;
- local path and checksum when available;
- an explicit `rights_basis` reviewed by a human;
- an `evidence_reference` containing at least one `timecode`, `page`, `line`, or `section` locator;
- one or more `evidence_ids` that exist in the `research.md` evidence ledger;
- transformation purpose;
- rights state;
- privacy state;
- placeholder state;
- human approval.

Use explicit rights states such as `pending`, `owned`, `licensed`, `public-domain`, `authorized`, or `human-approved`. A rights state is not a rights basis: record why the exact excerpt is considered usable and who reviewed that decision. Unknown or pending rights, a missing locator, or an unlinked evidence ID blocks `publish-approved` status.

## Rights boundary

Keep third-party excerpts short, necessary, and transformative, but do not present that editing practice as legal clearance. A human must approve the exact excerpts and rights basis before publication.

Do not commit third-party source media to the reusable Skill repository. Store it only in the production project according to the owner's authorization.
