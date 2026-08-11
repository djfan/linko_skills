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
- Record one continuous master capture with extra handles for editing.

Prefer deterministic Playwright recipes for known flows. Use computer use only for unfamiliar UI or selector recovery.

## Recommended capture recipe

1. Copy the source URL.
2. Open Add Link.
3. Paste and submit the URL.
4. Show the Resource appearing.
5. Create a structured hierarchical Note beneath the Resource.
6. Save or Publish the Note.

Keep the operation continuous in one master recording; edit only typing and network waits. Record the capture transport as native screen recording or browser-only screencast. Verify that the player timeline advances and that first, middle, and final frames change. Keep the cursor visible when it explains an action.

Preserve the raw master, edited cut, and an edit-decision list with removed intervals and reasons. Do not cut inside clicks, pointer motion, scrolling, loading-to-success, Resource appearance, or Save state changes. Verify in the real UI or DOM which entity owns each title, tag, hierarchy, and state. Never move or overlay a tag in post-production.

An authored bridge may show intent or transfer but never a successful Linko action. Stop before the first real action and match the authenticated first frame in fps, geometry, text, URL, and button state. Save A/B or overlay proof. The bridge remains a separate `authored-bridge` asset and cannot satisfy Linko capture approval.

## CTA preflight

Do not claim `Follow me on Linko`, `Follow my notes on Linko`, or viewer-accessible full notes until a public destination and the requested action are verified. Without that proof, use a generic creator-follow CTA and describe Linko only as the creator's own research trail.
