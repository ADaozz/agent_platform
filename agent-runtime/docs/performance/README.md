# Generation-time interaction performance

The reported symptom was opening menus and typing while a generation is streaming.
The main measured frontend cause was re-running Markdown parsing and sanitization
for every historical answer on composer/menu updates and incoming stream batches.
A separate Markdown component now caches its sanitized HTML by content. Both the
standalone frontend and the ITAM embedded frontend use this behavior.

Completed, folded execution details are mounted only when opened, and closed step
bodies avoid serializing large arguments/output. Full text stays in the event history
and remains available when reopened. Office catalogs no longer deep-traverse entire
page/slide trees just to report their root replacements. DOCX previews decode the
page being shown before swapping; offscreen thumbnails remain lazy instead of
blocking on decoding the whole document at full resolution.

Session polling now opts into `/api/agent/sessions?summary=true`. SQLite projects
only sidebar fields and a bounded first-line title; it avoids document-directory
walks and model-config decryption for every historical session. The active session
is loaded in detail, and overlapping refreshes share their request. The embedded
sidebar already suspended its periodic poll on `/agent`; the change also shares
its in-flight initialization request with the workspace. The original full-list API
and ownership behavior stay available. DOCX metadata reads avoid unpacking snapshots
and deserializing history on preview/status paths.

Measured locally, using Chromium with 80 historical answers of 3771 characters,
22-character typing samples and continuous generation snapshots every 40 ms:

| Metric | Before | After |
| --- | ---: | ---: |
| Menu open to next animation frame, median of 15 opens | 73.2 ms | 13.7 ms |
| Typing 22 characters while streaming, median of 3 samples | 1890.49 ms | 127.17 ms |
| List request with 50 sessions and 500 files, median of 5 | 315.930 ms | 11.181 ms |
| Session-list response size | 4,784,041 bytes | 12,141 bytes |

The generation input/menu fixture ran sequentially against the original and changed
production builds. The sidebar comparison uses the compatible full-list route and
the compact route on the same seeded database. The embedded production frontend was
also exercised through its auth/gateway adapter with mocked responses: no page errors;
menu-opening median 7.7 ms in that run. These fixtures establish local differences,
not production latency guarantees or a measurement of the user's machine.

Validation: 179 DOCX/platform Python tests, 18 conversation/Office state tests,
both production frontend builds (including embedded TypeScript checks), execution
interaction browser tests, and a 12-page native DOCX browser run passed. The browser
runs cover generation steering, independent output scrolling, folding/reopening,
cancellation/failure replay, focus, persisted state and cross-session file isolation.
No model request or live credential is needed for the performance fixture.

The browser performance fixture (`tests/performance.mjs`) lived in the standalone
runtime frontend and was removed with it; the numbers above are kept as a historical
record. The session polling benchmark remains reproducible:

```sh
python scripts/benchmark_session_polling.py
```

The browser fixture mocks only backend data and the EventSource transport; it runs
the real compiled Vue rendering and menu handlers. Native process/DOCX browser runs
supply the separate end-to-end behavior checks. Raw measurements are alongside this
file. Longer transcripts still have full-history timeline projection, so incremental
projection/virtualization is a possible follow-up if profiling larger sessions shows
that remaining path dominates after the Markdown/layout work is removed.

An extra legacy PPTX browser fixture was attempted but is not counted as a pass:
it inferred all completed operations from status.history, which intentionally lists
only snapshots whose blobs survive retention. After the early revisions were pruned,
the fixture retried plan-000 and hit the existing idempotency conflict. This path is
unchanged by this patch; the fixture needs separate progress tracking. Its attempted
run therefore does not establish PPTX browser acceptance for this performance change.
