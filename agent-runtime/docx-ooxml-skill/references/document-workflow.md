# Section authoring contract (v1)

All commands run through the existing main Agent `execute`. No new Agent or ZIP engine.
The existing `apply-one`, `checkpoint`, `restore` and legacy `apply` remain available.

## Plan

`validate-plan tmp/document-plan.json` validates the plan without opening a document.
The normative field constraints are in `document-plan.schema.json`, with cross-field
uniqueness, resource ownership and citation validation in `scripts/document_plan.py`.

```json
{"version":1,"document_id":"report","title":"Research report","page_target":20,
 "design":"academic","references":[{"id":"source-1","text":"Author, title, year"}],
 "sections":[{"id":"intro","title":"Introduction","requirements":"Explain the evidence",
 "block_ids":["intro-h","intro-body"],"equations":[],"figures":[],"tables":[],
 "citations":["source-1"],"styles":["Heading1","Normal"]}]}
```

Persist with a request envelope:

```json
{"document_id":"report","base_revision":0,"operation_id":"plan-1","plan":{}}
```

Replace `{}` with the validated plan; submit `save-plan files/report.docx tmp/plan-request.json`.
Plan edits increment Revision and preserve content; changed sections need review.

## Section transaction

```json
{"document_id":"report","base_revision":1,"operation_id":"intro-v1","section_id":"intro",
 "operations":[{"type":"append_paragraph","block_id":"intro-h","style":"Heading1","text":"Introduction"},
 {"type":"append_paragraph","block_id":"intro-body","text":"Evidence and context."}]}
```

Limits: 1–80 operations, 120000 serialized Unicode characters, 20 MiB unique input
resources, 64 MiB uncompressed candidate package. Each atomic operation keeps its
existing 24000-character and semantic limits. Assets must resolve inside asset-root.
Operations and anchors must belong to the planned section. Global page/header/theme
edits and section.clone use apply-one. Failed candidate edits change neither file,
Revision nor event journal. Durable commit followed by publication failure is
recovered by the existing SQLite pending_publish mechanism, then replayed by ID.
A render error is a post-commit check failure, not a failed transaction.

## Checks and repairs

`check-document files/report.docx [--section-id intro] [--final]` always checks the
current full reflow. The optional section ID records the generation checkpoint;
page checks remain global because Word pagination crosses section boundaries.
The final check also reports missing planned blocks. Every finding has a stable
`target_id`, `code`, `block_id` where a source block can be reliably identified,
`deterministic` and an optional bounded repair operation. Geometry without a unique
source maps to candidate `block_ids` and a page; it never fabricates a block ID.

Checks cover OOXML/resource relationships, empty equations, invalid charts, bookmarks,
REF/PAGEREF targets, heading hierarchy/keep-with-next, long-table pagination, rendered
overflow, blank pages, font substitution and orphan headings/lines. Ambiguous or
unsupported template structures are reported or rejected, never flattened.

`repair-document ... --base-revision N --operation-id repair-id` only applies the
checker-owned allowlist: heading keep-with-next, recognized widow/orphan control,
long-table row/header/keep rules, declared single-page component spacing, cached
TOC destination pages and explicitly planned section numbering properties.
It rechecks and reports unresolved issues. It never accepts arbitrary repair payloads
or modifies text. Fonts, ambiguous whitespace, complex template layout and semantic
suggestions require user/Agent investigation. Identical rendered page fingerprints
retain previous manual review evidence; changed pages lose it after real reflow.

## Main-Agent visual review

The main Agent reviews the pages itself; neither the CLI nor the host calls a model.
`review-images` requires a passed final check for the current Revision and its open
visual request. It verifies that the cached render still has the checked page
pixels, then returns the page PNGs, a numbered `document-sheet.png` of every page,
the guidance (page checks: legibility, spacing, tables, media_balance,
heading_hierarchy, equations, whitespace, completeness; document checks:
consistency, structure, rhythm, design_fit) and `review-context.json`.

`submit-review` validates the whole request before writing anything. Every check
needs a verdict and visible evidence; a page `block_id` that is not on that page is
cleared. Any issue, or a failed/issues verdict, makes the page or document `issues`;
an uncertain verdict or check stays `uncertain`; only a clean answer is `passed`.
The document review is accepted only after every page has a current review. Results
are written to `aesthetic_reviews` / `document_review` with `reviewer: main_agent`,
Document ID, Revision, page fingerprint(s), request ID, render and pixel hashes, then
the delivery state is recomputed. Visual results are advisory and cannot change DOCX
bytes. API/UI expose the current document_check and aesthetic_reviews; a new
Revision invalidates those results immediately.

## Reproducible acceptance

Run `scripts/benchmark_docx_workflow.py` in the runtime parent for academic and
technical corpora. The report records actual page count, one command per section,
legacy protocol call count, revisions, elapsed render/check time and local repairs.
Page targets are soft and depend on LibreOffice/fonts. No page breaks are inserted.
Use `pytest --import-mode=importlib` when running DOCX and PPTX suites together
because their existing test module basenames overlap.

## Quality contract 2 (new CLI documents)

The authoritative final check uses the immutable revision PDF and OOXML semantic
objects. `repair_targets` include revision, page (null when not uniquely mapped),
stable block ID, error code, severity, repairability and exact safe operation.
Normal wrapping, same-paragraph superscripts, table-cell text and header/footer
furniture are excluded from naive box-overlap claims. Ambiguous geometry is
reported without fabricated IDs. Complex edits continue to reject lossily.

`check-document --final` repairs only safe deterministic targets, with no fixed
round limit. Each commit re-renders; all prior revision review results become invalid.
A remaining finding blocks formal acceptance and leaves the draft downloadable.
Stop reasons are persisted for the current revision. Unchanged content, repeated
error evidence, worsening/stationary geometry, and recurring states terminate
autonomous repair; repeating a final check does not restart a stopped revision.
A real local content edit creates a new revision, which must be checked again.
`--diagnostic-only` and `repair-document` support investigation,
not bypasses. New CLI init defaults to contract 2; persisted legacy contract 1
state remains backward compatible.

Agent page reviews cover every page; the separate `document_review` uses every page
in a numbered thumbnail sheet and the completed page reviews. Both are
version/pixel/request bound and never mutate content. Three UI states are separate:
deterministic passed/failed/pending, page visual passed/issues/pending/unavailable,
and document visual passed/issues/pending/unavailable. Final output records
revision/design, repair attempts/unresolved targets, reviewed/issue pages and
visual completion. Pending or unavailable reviews are drafts, never fake passes.

A plan section may set `kind`, `single_page`, `numbering:{format,start}` and
`continued_label`. These express component requirements; sections are authoring
units and physical pages are review units. `numbering` audits real Word section
properties; it does not silently insert new section boundaries into templates.

### Shared DOCX / PPTX repair progress policy

Both formats use platform_app/office_repair.py. It compares stable deterministic
issue identities and evidence, optional measured defect magnitudes, and package
contents excluding ZIP timestamps. Visual model suggestions never enter repair
progress or authorize an edit. Every local repair must be rendered and checked.
Continue beyond three attempts when targets resolve or measured geometry improves.
Stop and retain the draft on no_progress, repeated_errors, repair_cycle, an unsafe
repair target or render failure; disclose remaining issues and the stop reason.
The former max_attempts Python/CLI argument is accepted for compatibility only
and no longer caps the loop. PPTX check-deck returns repair_control and a stopping
next_action for the main Agent; it never rewrites a deck or applies visual advice.
