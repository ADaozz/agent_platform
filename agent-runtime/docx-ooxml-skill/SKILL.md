---
name: docx-ooxml-author
description: Generate and revise editable DOCX files from a template when one exists, using cloned sections, named styles and content controls. A blank package is only the fallback. Section transactions, document plans, local repairs and asynchronous host visual review, with real LibreOffice pagination.
compatibility: Python 3.10+, lxml, Pillow, PyMuPDF, LibreOffice. Runs through execute; no separate Agent or MCP server required.
metadata:
  version: "0.6.0"
  maintainer: "local"
---

# DOCX authoring

This skill does not register a new Agent tool. Run `scripts/office_docx.py` through `execute`, from the task workspace root (the directory that contains `files/` and `tmp/`; `execute` starts there). In the platform the path is `/agent-skills/docx-ooxml-author/scripts/office_docx.py`. Use the main Agent only. One execute call submits one bounded atomic operation or one planned section transaction. Do not add an Agent, loop CLI commands, or write the ZIP yourself.

## Deliverable location (hard rule)

- `files/<name>.docx` is the **only working copy and the deliverable**, from `init` onward. The platform versions and previews only documents under `files/`; a document anywhere else is invisible to the user.
- Always pass the document as `files/<name>.docx`, operation requests as `tmp/<name>.json`, and `--asset-root tmp`. Do not write the document to `tmp/` or the workspace root, and do not build it elsewhere and copy it in at the end.
- `files/` holds the deliverable and the user's uploads, nothing else. Every file there is shown to the user as output. One requested document means one `.docx` in `files/`: never create probe, test or draft documents there. To try an operation, apply it to the deliverable and, if it does not work, go back with `restore files/<name>.docx --revision <good> --base-revision <current> --operation-id <new id>`.
- Intermediate material goes in `tmp/`: operation requests, scripts, figures and chart images (`tmp/assets/fig1.png`), downloaded sources and your own renders. Inserted images are embedded in the document, so their source files stay in `tmp/`. Only an image the user uploaded is inserted from `files/`, with `--asset-root files` for that operation.
- Uploaded files are in `files/`, so an uploaded template is `files/<template>.docx`.

Prefer a template's sections, paragraphs, named styles, content controls and tables. Author a WordprocessingML fragment only when the template has no suitable block and the atomic operations cannot express the change. Do not claim a page was checked unless you inspected its LibreOffice render.

## Workflow (default for multi-section documents)

1. Select an uploaded template first. With no template, run `list-styles` and
   `inspect-style academic` (also consulting, technical, business), then use
   `init --document-id report --output files/report.docx --design academic`.
   An explicit Design MD path is accepted; its `docx-design` JSON block maps to
   named Word paragraph/table styles and page dimensions. `--template` takes
   precedence and leaves all template styles intact, even if `--design` is present.
2. Write `tmp/document-plan.json`, validate it with `validate-plan`, then persist
   it using `save-plan files/report.docx tmp/plan-request.json`. The plan contains
   section requirements, stable block IDs, equations/figures/tables, references
   and styles. Page count is a soft target; never manufacture fixed pages.
3. Submit each section with `apply-section files/report.docx tmp/section.json
   --asset-root tmp`. It uses the existing atomic operations in memory, commits
   once and checkpoints the entire reflow once. Read `status` after each call.
   Validation/mutation failure rolls the entire transaction back. A render
   failure after a successful commit leaves that revision recoverable, reports
   the failure and blocks the next section until checked again.
4. Run `check-document files/report.docx --final`. **Mandatory:** the current
   immutable revision must undergo actual PDF geometry/collision and layout checks.
   New documents use quality contract 2, including user templates. Final checks
   automatically run up to three deterministic, Block-ID-local repair transactions,
   re-rendering and rechecking each time. `--diagnostic-only` reports without repairs
   and never waives the gate. `repair-document --max-attempts 1..3` can explicitly
   resume repairs. Unrepairable findings require a local Agent edit or an explicit
   failure report; never silently ignore them, delete necessary content or shrink
   all text. A failed final check cannot be accepted. Keep the downloadable draft.
5. After the deterministic final pass, the shared platform Office service queues
   **every page** for visual review concurrently, then separately executes
   `document_review` over all numbered thumbnails, section mapping and page results.
   Both are actual model invocations, bound to Document ID, Revision, pixels and
   request ID. Missing/failed image models return unavailable. Visual advice never
   edits the file. A revision or reflow invalidates affected review evidence; stale
   jobs cannot update new content. Do not replace model review with guessed verdicts.
6. `finalize files/report.docx --base-revision N` records DOCX + three independent
   states, design ID, repair counts and unresolved findings. Formal acceptance
   requires the final deterministic pass and completed page AND document visual
   passes. Pending/unavailable visual results and remaining visual issues remain
   clearly labelled downloadable drafts. CLI-only execution has no host visual model,
   so cannot claim visual completion. Persisted legacy contract 1 documents retain
   their old APIs and gates; do not select legacy mode to bypass acceptance.

For domestic research documents without a template, inspect and select
`cn-thesis-general`, `cn-engineering-thesis`, `cn-journal-paper` (default two
columns; `init --columns 1` also supported), or `cn-research-report`. The original
academic/technical/business/consulting designs remain available. Chinese/Latin
fonts and named component styles are separate. Read sources and their verification
scope; default sizes are design choices, not universal national mandates. Official
institution/journal templates override generic designs. Do not assert GB/T citation
compliance or bibliographic truth without actual source information.

Declare section `kind` (cover/abstract/toc/body/references/appendix), `single_page`
where appropriate, `numbering` format/start and any required `continued_label` in
the plan. Use CoverTitle/CoverDate, AbstractTitle/AbstractBody, Caption, Equation,
Reference and TableText styles. Numbering switches require real OOXML sections or
a supplied template; if lossless section edits are unavailable, report the issue.
The final audit compares section numbering and rendered TOC destinations rather
than treating visible leader dots as a valid TOC. Page targets remain soft goals.

To change course, submit a replacement plan with a new operation ID and current
base revision. Unaffected document bytes and section content are retained; affected
sections are marked `needs_review`. Inspect their existing block IDs and update
those blocks with apply-section or apply-one. Removing a section from the plan
never silently deletes existing content. Restore restores the plan associated
with the selected snapshot. See `references/document-workflow.md` for payloads.

## 1. Choose a template

Look for an uploaded DOCX before creating a blank file. `import-template` assigns block ids in memory, writes a manifest, and does not modify the user's file.

Template path, the default:

```sh
python "$S" import-template --template files/input.docx --template-id report --license-note "user file"
python "$S" init --document-id report --output files/report.docx --template files/input.docx
python "$S" status files/report.docx
python "$S" apply-one files/report.docx tmp/operation.json --asset-root tmp
python "$S" check-document files/report.docx --final
python "$S" finalize files/report.docx --base-revision N
```

Blank path, only when nothing suitable exists:

```sh
python "$S" init --document-id report --output files/report.docx
python "$S" apply-one files/report.docx tmp/operation.json --asset-root tmp
python "$S" check-document files/report.docx --final
python "$S" finalize files/report.docx --base-revision N
```

`$S` is the CLI path above. Repeat it on every execute call.

## 2. Template operations

`apply-one` remains one bounded semantic operation; `apply-section` is one planned chapter of these operations. `section.clone` may copy the blocks of one heading section inside that limit (40 blocks, 20000 characters). This limit still applies inside a section transaction; do not submit the whole document or a ZIP write.

- `section.clone` copies a heading and the blocks up to the next same-or-higher heading, including their styles.
- `block.clone` copies one paragraph or table. `rows` replaces cell text and does not leave older paragraphs behind.
- `slot.fill` fills one content control `tag`, or one paragraph `block_id`. Other content controls stay as they are. Rich text, nested controls, mixed run styles, images, fields and hyperlinks are rejected until a lossless edit exists.
- `part.replace_text` changes one occurrence in the header or the footer.
- `document.recolor` updates the theme and named styles, plus direct colors and shading that belong to that theme. Pictures are preserved. `unhandled` lists `unmapped` and `unsupported` colors with a location. `recolor_complete: true` means that list is empty.

Word repaginates. Do not insert page breaks to manufacture a page count.

## 3. Fallback

`append_paragraph`, `append_table` and `insert_image` add content with an existing style. `insert_block` is one bounded paragraph fragment, not the normal way to write. Repairs (`replace_text`, `set_paragraph_style`, `set_paragraph_format`, `delete_block`, `set_table_format`, `set_page`) stay available. Payloads are in `references/operations.md`. The old batch plan is in `references/legacy-operations.md` and is not this workflow.

## 3a. Academic content

Reports with formulas, figures and references use these native operations, through apply-one or a planned apply-section transaction. Do not hand-build OMML, charts, fields or a ZIP in `tmp/` to get them.

- Headings: `append_paragraph` with `Heading1`, `Heading2` or `Heading3` (multi-level headings feed the table of contents).
- `insert_toc`: a Word table of contents, rebuilt from the headings after every operation.
- `insert_equation`: native, editable Office Math from LaTeX; `numbered: true` adds `(n)`.
- `insert_chart`: a native Word chart with an embedded workbook (column, bar, line, area, pie, doughnut, scatter, bubble).
- `insert_caption`: `图`/`表` numbering that renumbers itself; give it a `ref_id`.
- Cross-references: write `{{ref:<ref_id>}}` inside `append_paragraph` text. Forward references are allowed; check `unresolved_references` in the result.
- Long tables: `append_table` up to 60 rows; the header row repeats across pages.
- Complex tables: `insert_table` with `colspan`/`rowspan`, column widths and alignment, cell fill, three-line or grid borders; `set_table_cell` edits one cell later.
- Character formatting and inline math: `runs` in `append_paragraph` (bold, italic, underline, size, colour, highlight, font, letter spacing, superscript/subscript, `{"math": ...}`), or `{{math:...}}` in text; `format_text` formats part of an existing paragraph.
- Citing headings: give a heading `ref_id`, then `{{ref:id}}` shows its text and `{{pageref:id}}` its page.
- Images: `insert_image` with `float: left|right` wraps text around it; `insert_image_row` places 2-4 images side by side with sub-captions.
- Headers and footers: `set_header_footer`, with `{{page}}` and `{{pages}}` for page numbers.

Payloads and limits are in `references/operations.md`.

## 4. Revisions and checkpoints

Use the current `base_revision`, a stable `block_id` and a stable `operation_id`. Repeat the same request after uncertain delivery. A conflict means read `status` and rebase. A failed operation does not increment the revision. Restore creates a new revision.

The legacy apply-one engine asks for a checkpoint after three additions. apply-section checks once at each section end, followed by a final check-document. Do not skip it by writing the package yourself. Failed automatic checks block further additions until the current content is repaired.

## 5. Render and finish

`checkpoint` renders with LibreOffice and records pages. Inspect those images. A vision-capable reviewer can call `review-page` with notes from that image. Text-only inspection cannot pass a page. A missing renderer is a failed checkpoint.

For legacy documents, `finalize --base-revision` requires the final checkpoint and a reviewed final page. New documents require final collision/layout checks plus both host visual reviews for formal acceptance; strict mode also retains its actual page approval gates. The file can be downloaded while visual review is pending; call it a draft until the pages have been seen. Never execute macros or embedded programs from a template.

## Request

```json
{"document_id":"report","operation_id":"op-0007","base_revision":6,"operation":{"type":"section.clone","source_block_id":"template-0013","block_id":"sec-next","heading":"实施范围","paragraphs":["第一段。","第二段。"]}}
```

Structures this skill will not silently simplify: merged or nested tables, mixed character styles, images inside a rewritten paragraph, fields, hyperlinks, and rich-text content controls. Those operations raise and leave the last good file in place.
