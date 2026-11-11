# DOCX OOXML Author Skill (v0.1)

A runnable Agent Skills-compatible foundation for **template-first** DOCX generation via WordprocessingML XML fragments, versioned patches, render-review loops and finalization gate.

This is a **bounded prototype**, not a comprehensive Microsoft Word editing engine. Advanced chart/SmartArt/field/section/object fidelity is listed in `references/extensions.md`.

Prerequisites: Python 3.10+, `pip install -r requirements.txt`, LibreOffice headless, fonts for your target language.

Usage: follow `SKILL.md`. Run from the task workspace root (the directory containing `files/` and `tmp/`), one atomic operation per command; the document lives in `files/` from `init` onward:

```bash
S=scripts/office_docx.py
python "$S" init --document-id report --output files/report.docx
python "$S" apply-one files/report.docx tmp/operation.json --asset-root tmp
python "$S" check-document files/report.docx --final
python "$S" finalize files/report.docx --base-revision N
```

The older candidate/plan batch commands (`apply`, `render`, `review-template`, `finalize --render-dir`) are kept for compatibility only and are described in `references/legacy-operations.md`; do not use them for new work. The input DOCX is never overwritten. Outputs are editable Office files, not page screenshots.

## Planned section workflow

See [the workflow contract](references/document-workflow.md) for Design MD, document-plan.json, apply-section transactions, full-document checks, local repair and shared asynchronous visual review. Existing atomic/legacy interfaces remain supported.

## Research quality acceptance

New CLI documents require final OOXML/PDF geometry checks, bounded local repairs,
all-page visual review and a separate whole-document visual review. The platform
shows the three statuses independently. Missing models remain Unavailable; pending
reviews and visual issues remain downloadable drafts. Uploaded templates retain
their styles. Four optional CN designs document separate Chinese/Latin fonts and
the source/verification scope of national and institutional requirements.

Reproduce the long-document acceptance (LibreOffice and CJK fonts required):

```sh
python agent-runtime/scripts/accept_docx_research.py --output /tmp/research-accept
# --live prompts for a DeepSeek key without storing it; actual model verdicts
# are retained, including issues. --review-existing retries the same document.
```
