# Office quality review UI

Both frontend distributions implement the same Office review view model and
components under `src/features/office/` (embedded: `src/agent-platform/features/office/`).
Their API adapters retain their own same-origin / authenticated ITAM gateway paths.

- `reviewModel.js` preserves backend states and maps them to pending / passed /
  issues / unavailable / stale. Stage status is presentation only; formal acceptance
  still comes from the backend. DOCX validates revision, active request and page
  fingerprints. PPTX validates its parent check, document request and fingerprints;
  explicitly retained unchanged-page renders show their original reviewed revision.
- `ReviewDisclosure.vue`, `ReviewIssueList.vue`, `ReviewMetadata.vue` share fold,
  status/counts, raw evidence, errors and action rendering. Slots preserve PPTX
  element highlights, dismissal and its custom issue content. Collapsed folds do
  not mount large issue lists. Raw model severity/confidence are never inferred.
- `delegate.js` uses the existing session steering endpoint while running/queued,
  and the existing message endpoint while idle. It carries identity, revision,
  page/slide, block/element, review and request identifiers and the original advice.
  Clicking Delegate is explicit user direction to the main Agent. Visual review
  itself is done by the main Agent (`review-images` / `submit-review`); "review
  again" and "review deck consistency" only send it a request through the same
  channels, and the host never calls a model. A sent request is shown as sent,
  never as resolved.
- DOCX page navigation rejects an out-of-date preview. Regions are shown only from
  the bound deterministic check's normalized `block_regions`: exact unique PDF
  paragraph matches or exact image-pixel digests. Repeated/ambiguous text, missing
  coordinates or multiple candidate regions degrade to page navigation with an
  explicit notice. Metadata projection adds coordinates without changing checks,
  generation, automatic repair or the Agent's visual review.
- Async snapshots are fenced against newer events. Same-version DOCX request
  generations retire old request IDs; changing revision clears issue/action scope.
  Review-result objects and delivery/finalized fields are fenced as one request-owned
  payload, including result events that omit the visual_request envelope. Unbound
  or mixed-generation payloads cannot update delivery flags; fresh request creation
  also invalidates previous delivery state.
  There is no human page approval; delegation and review requests never approve a page.

Run from repository root:

```sh
node --test agent-runtime/tests/office-review.test.mjs agent-runtime/tests/documents.test.mjs
node agent-runtime/frontend/tests/office-review.e2e.mjs
npm run build --prefix agent-runtime/frontend
npm run build --prefix frontEnd
```

The Chromium suite mounts the actual Vue panels from **both** distributions and
uses controlled HTTP Office fixtures with real rendered PNGs. It verifies three
independent folds, page and verified-region navigation, missing coordinates,
metadata, running/idle Agent delegation, HTTP errors/retry, revision/request
staleness, unchanged PPTX highlighting, dismissal and whole-deck navigation.
It records screenshots and request evidence under `frontend/test-results/office-review/`.
This is UI protocol regression evidence; it does not claim new live model calls.
Backend tests separately validate actual PDF coordinates and the real FastAPI
steering route into the session runner.
