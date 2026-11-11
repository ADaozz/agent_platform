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
checker-owned allowlist: heading keep-with-next, recognized widow/orphan control and long-table row/header/keep rules.
It rechecks and reports unresolved issues. It never accepts arbitrary repair payloads
or modifies text. Fonts, ambiguous whitespace, complex template layout and semantic
suggestions require user/Agent investigation. Identical rendered page fingerprints
retain previous manual review evidence; changed pages lose it after real reflow.

## Background visual review

The host shares `platform_app.office_review` queue, image checks, timeout/retry,
model client and private SQLite review ledger with PPTX. DOCX supplies only its
page schema, prompt, snapshot rendering and compare-before-apply adapter. Jobs bind
Document ID, Revision and the actual page fingerprint; stale jobs are recorded as
unapplied and cannot update current state. Pending pages resume after host restart.
Model input and ledger remain outside the Agent sandbox. Visual results are
advisory and cannot change DOCX bytes. API/UI expose the current document_check
and aesthetic_reviews; a new Revision invalidates those results immediately.

## Reproducible acceptance

Run `scripts/benchmark_docx_workflow.py` in the runtime parent for academic and
technical corpora. The report records actual page count, one command per section,
legacy protocol call count, revisions, elapsed render/check time and local repairs.
Page targets are soft and depend on LibreOffice/fonts. No page breaks are inserted.
Use `pytest --import-mode=importlib` when running DOCX and PPTX suites together
because their existing test module basenames overlap.
