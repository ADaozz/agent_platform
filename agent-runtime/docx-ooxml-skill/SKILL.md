---
name: docx-ooxml-author
description: Generate and revise editable DOCX files from a template when one exists, using cloned sections, named styles and content controls. A blank package is only the fallback. Section transactions, document plans, local repairs and main-Agent visual review of real LibreOffice page renders.
compatibility: Python 3.10+, lxml, Pillow, PyMuPDF, LibreOffice. Runs through execute; no separate Agent or MCP server required.
metadata:
  version: "0.6.1"
  maintainer: "local"
---

# DOCX authoring

This skill does not register a new Agent tool. Run `scripts/office_docx.py` through `execute`, from the task workspace root (the directory that contains `files/` and `tmp/`; `execute` starts there). In the platform the path is `/agent-skills/docx-ooxml-author/scripts/office_docx.py`. Use the main Agent only. One execute call submits one bounded atomic operation or one planned section transaction. Do not add an Agent, loop CLI commands, or write the ZIP yourself.

## Deliverable location (hard rule)

- `files/<name>.docx` is the **only working copy and the deliverable**, from `init` onward. The platform versions and previews only documents under `files/`; a document anywhere else is invisible to the user.
- Choose the output path and `document_id` once, then reuse that pair for every write, repair and check. The platform binds the ID to the first file it sees. Reinitializing under another filename with that ID leaves the preview bound to the first file. Revise the existing document in place or restore a known-good revision at the same path. Use distinct IDs and paths only for separate requested deliverables.
- Always pass the document as `files/<name>.docx`, operation requests as `tmp/<name>.json`, and `--asset-root tmp`. Do not write the document to `tmp/` or the workspace root, and do not build it elsewhere and copy it in at the end.
- `files/` holds the deliverable and the user's uploads, nothing else. Every file there is shown to the user as output. One requested document means one `.docx` in `files/`: never create probe, test or draft documents there. To try an operation, apply it to the deliverable and, if it does not work, go back with `restore files/<name>.docx --revision <good> --base-revision <current> --operation-id <new id>`.
- Intermediate material goes in `tmp/`: operation requests, scripts, figures and chart images (`tmp/assets/fig1.png`), downloaded sources and your own renders. Inserted images are embedded in the document, so their source files stay in `tmp/`. Only an image the user uploaded is inserted from `files/`, with `--asset-root files` for that operation.
- Uploaded files are in `files/`, so an uploaded template is `files/<template>.docx`.

## When to create the document (hard rule)

Before creating `files/<name>.docx`, choose the template or style, validate a whole-document outline with `validate-plan`, and prepare the first section's real content and operation request. Research, write and prepare assets for later sections as those sections come up. Do not draft the whole document, generate all figures, or test formulas for later sections before the first write.

As soon as the first section is ready, run `init`, `save-plan` and the first `apply-section` in consecutive calls. For a single atomic write, run `init` then the first real `apply-one`. Prepare the requests before `init` so the user sees real content promptly. When editing an uploaded document, start from the existing file.

Prefer a template's sections, paragraphs, named styles, content controls and tables. Author a WordprocessingML fragment only when the template has no suitable block and the atomic operations cannot express the change. Do not claim a page was checked unless you inspected its LibreOffice render.

## Workflow (default for multi-section documents)

1. Select an uploaded template first. With no template, use the sole bundled
   design, `cn-thesis-general`. Read it with `inspect-style cn-thesis-general`.
   An explicit user-provided
   Design MD path is accepted; its `docx-design` JSON block maps to named Word
   paragraph/table styles and page dimensions. Do not create the file yet.
2. Write `tmp/document-plan.json` and validate it with `validate-plan`. Record
   each section's purpose and stable block IDs. For the first section, check
   that the request's block IDs and any explicit paragraph styles match the
   plan. Refine later sections with `save-plan` before writing them when their
   requirements, blocks, references or assets change. Page count is a soft
   target. `save-plan` needs the document, so it waits until the next step.
3. When the first section is ready to write, create the document and start
   writing immediately:
   `init --document-id report --output files/report.docx --design cn-thesis-general`
   (or `--template files/input.docx`; `--template` takes precedence and leaves
   all template styles intact, even if `--design` is present), then
   `save-plan files/report.docx tmp/plan-request.json`, then
   `apply-section files/report.docx tmp/section.json --asset-root tmp`.
   `apply-section` uses the existing atomic operations in memory, commits
   once and checkpoints the entire reflow once. Read `status` after each call.
   Then prepare and write the next section on the same file and `document_id`.
   Validation/mutation failure rolls the entire transaction back. A render
   failure after a successful commit leaves that revision recoverable, reports
   the failure and blocks the next section until checked again.
4. Run `check-document files/report.docx --final`. **Mandatory:** the current
   immutable revision must undergo actual PDF geometry/collision and layout checks.
   Report visible defects. Normal hanging Chinese punctuation and sub-point image
   margin rounding do not require repair.
   New documents use quality contract 2, including user templates. Final checks
   automatically run deterministic, Block-ID-local repair transactions without a
   fixed round cap, re-rendering and rechecking each time. `--diagnostic-only`
   reports without repairs
   and never waives the gate. `repair-document` can explicitly resume repairs.
   Each attempt must re-render
   and recheck. Continue only while deterministic evidence makes progress; stop on
   unchanged content, repeated errors or recurring document/error states, and report
   the stop reason with the remaining targets. Revision increments alone are not
   progress. After a no-progress/repeated-error/cycle stop, report the remaining
   issues and retain the draft; do not make unrelated edits or add a Revision to
   restart autonomy without user direction.
   Unrepairable findings require a local Agent edit or an explicit
   failure report; never silently ignore them, delete necessary content or shrink
   all text. A failed final check cannot be accepted. Keep the downloadable draft.
5. After the deterministic final pass, **you (the main Agent) review the rendered
   pages yourself**; no other model or external API is called.
   `review-images files/report.docx` returns every page PNG (absolute path), a
   numbered overview sheet, the review `guidance`, a `context_file` (design,
   section mapping, page blocks, deterministic checks) and a `submit` template.
   Open **every page** with `read_file`, then write `tmp/visual-review.json` and run
   `submit-review files/report.docx tmp/visual-review.json` with
   `{"revision":N,"request_id":"…","pages":[{"page":1,"review":{status,summary,checks,issues}}]}`.
   Pages may be submitted in batches. After every page is reviewed, open the
   overview sheet and submit `"document":{"review":{…}}` for cross-page issues
   (each issue lists its `pages`). A malformed request is rejected as a whole and
   records nothing; fix it and resubmit. Results are bound to Document ID,
   Revision, page pixels and request ID; a revision or reflow invalidates them.
   Never give a verdict for a page you did not open. If the current model cannot
   read images, submit `{"page":N,"unavailable":"reason"}` (or
   `"document":{"unavailable":"reason"}`) instead of guessing. Visual advice never
   edits the file.
6. `finalize files/report.docx --base-revision N` records DOCX + three independent
   states, design ID, repair counts and unresolved findings. Formal acceptance
   requires the final deterministic pass and completed page AND document visual
   passes. Pending/unavailable visual results and remaining visual issues remain
   clearly labelled downloadable drafts. Persisted legacy contract 1 documents retain
   their old APIs and gates; do not select legacy mode to bypass acceptance.

The bundled `cn-thesis-general` design defines Chinese and Latin fonts
separately and uses named component styles. Read sources and their verification
scope; default sizes are design choices, not universal national mandates. Official
institution/journal templates override generic designs. Do not assert GB/T citation
compliance or bibliographic truth without actual source information.

For `cn-thesis-general`, insert the table caption (`insert_caption`, label
`表` or `Table`) immediately before the table. It uses the centered 10.5 pt
(`五号`) `TableCaption` style with a Song-style Chinese font. Use the school's
font when specified. Tables default to three-line borders. Place any table note
in a `TableNote` paragraph immediately after the table. Insert the centered
figure caption immediately after the image. Keep the image and its caption on
the same page, and use the table caption's keep-with-next style above the table.

In `cn-thesis-general`, plan the TOC and references with `kind: toc` and
`kind: references`. Use `insert_toc` with the title 目录 and two or three
levels. The TOC2 and TOC3 indents (about one and two characters) are style
defaults. Follow the school template or explicit user formatting when supplied.
Give the TOC and references their own pages, including any continuation pages.
Start the next component on a fresh page after the last page of the TOC or
references, even if space remains. The body then flows normally. Start references
and the following components with a heading paragraph so the planned workflow
can apply the page break. When authoring without a plan, set `page_break_before: true`
with `set_paragraph_format` on the references heading and the headings that
follow these components. Use the native TOC field and the final rendered page
number check to populate the page numbers from their actual destinations.

Declare section `kind` (cover/abstract/toc/body/references/appendix/acknowledgments)
and any required `continued_label` in the plan. Create a separate `abstract` entry
for each language. Set `single_page` where required. In `cn-thesis-general`, plan-based authoring automatically
hides the cover page number, uses continuous uppercase Roman numerals for the
abstracts and TOC, and restarts Arabic numbering at 1 for the first body chapter.
References, appendices and acknowledgments continue body numbering. The native
PAGE field is centered in the footer in Times New Roman 10.5 pt. Use `numbering`
only for explicit overrides. Switch numbering with a next-page section break.
Use paragraph page breaks for new chapters, references and acknowledgments
within the same numbering sequence. For Heading 2/3, keep the title with the
next paragraph. Follow any school template supplied by the user.
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
python "$S" review-images files/report.docx
python "$S" submit-review files/report.docx tmp/visual-review.json
python "$S" finalize files/report.docx --base-revision N
```

Built-in design path when no template is supplied:

```sh
python "$S" init --document-id report --output files/report.docx --design cn-thesis-general
python "$S" apply-one files/report.docx tmp/operation.json --asset-root tmp
python "$S" check-document files/report.docx --final
python "$S" review-images files/report.docx
python "$S" submit-review files/report.docx tmp/visual-review.json
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

- Headings: `append_paragraph` with `Heading1`, `Heading2` or `Heading3`. With `cn-thesis-general`, pass only the heading text. Word's multilevel list supplies chapter and section numbers, and the TOC refresh includes them. Use `Normal` for body text (12 pt, SimSun for Chinese, first-line indent of two characters).
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

`checkpoint` renders with LibreOffice and records pages. Inspect those images. For legacy documents and strict-mode page gates, call `review-page --reviewer main_agent` with notes from the image you opened. Text-only inspection cannot pass a page. A missing renderer is a failed checkpoint.

For legacy documents, `finalize --base-revision` requires the final checkpoint and a reviewed final page. New documents require final collision/layout checks plus your page and document visual reviews (`submit-review`) for formal acceptance; strict mode also retains its actual page approval gates. The file can be downloaded while visual review is pending; call it a draft until the pages have been seen. Never execute macros or embedded programs from a template.

## Request

```json
{"document_id":"report","operation_id":"op-0007","base_revision":6,"operation":{"type":"section.clone","source_block_id":"template-0013","block_id":"sec-next","heading":"实施范围","paragraphs":["第一段。","第二段。"]}}
```

Structures this skill will not silently simplify: merged or nested tables, mixed character styles, images inside a rewritten paragraph, fields, hyperlinks, and rich-text content controls. Those operations raise and leave the last good file in place.
