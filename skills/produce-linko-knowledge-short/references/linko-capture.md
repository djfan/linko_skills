# Linko capture

## Capability preflight

Inspect the operations actually available through the active Linko tools and browser session. Do not infer capabilities from tool names. Record at least:

- Linko read access;
- resource add support;
- note write or edit support;
- resource edit or delete support;
- authenticated browser availability;
- public CTA destination availability.

When cleanup cannot be automated, add exact manual cleanup steps to `project-state.json`.

## Authentication boundary

Linko authentication is host-managed. Do not implement OAuth, token refresh, credential export, or transport setup inside the Skill. If capture requires an unavailable authenticated browser, set:

```json
{
  "status": "blocked",
  "blocker": "authenticated-capture-unavailable"
}
```

An approved screenshot sequence may demonstrate layout in a draft, but it must be marked `placeholder: true`, described as a screenshot prototype, and rejected by release validation.

## Privacy-safe capture

- Use a dedicated demo account and synthetic or approved notes.
- Record around 1440×900 or another readable desktop size, then crop later.
- Hide profile identifiers, notifications, unrelated recommendations, and private notes.
- Verify that every note, resource, and connection shown exists as represented.
- Record one action per clip with extra handles for editing.

Prefer deterministic Playwright recipes for known flows. Use computer use only for unfamiliar UI or selector recovery.

## Recommended capture recipe

1. Open Add Resource.
2. Paste or select the source.
3. Submit and show the resource appearing.
4. Open the relevant note.
5. Reveal one connection or related item.

Remove network wait and dead cursor time in the edit. Keep the cursor visible when it explains an action.

## CTA preflight

Do not claim `Follow me on Linko`, `Follow my notes on Linko`, or viewer-accessible full notes until a public destination and the requested action are verified. Without that proof, use a generic creator-follow CTA and describe Linko only as the creator's own research trail.
