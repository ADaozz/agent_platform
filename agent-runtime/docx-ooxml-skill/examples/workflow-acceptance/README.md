# DOCX workflow acceptance evidence

Generated with the existing atomic engine and LibreOfficeDev 26.8 on Linux.
The editable DOCX files are synthetic stress fixtures, with native equations,
charts/workbooks, headings, TOC and cross references (academic), and multi-level
headings plus five long tables (technical). No fixed page breaks are inserted.

| Case | Actual pages | Tool invocations | Final Revision | Repairs |
| --- | ---: | ---: | ---: | ---: |
| Academic | 20 | 13 | 9 | 0 |
| Technical | 30 | 11 | 7 | 1 |

The same academic content was also executed through the unchanged apply-one
protocol: 142 tool invocations, Revision 105 and 20 pages. Measured call reduction
is **90.85%** (13 vs 142). The legacy trace records publication as visually pending;
no visual approval was invented to complete the count. Its final automatic checks
passed. The estimated legacy protocol count in the benchmark code is conservative;
the measured trace is the comparison authority here.

The technical case detected one real paragraph line isolated across a page boundary.
A local `widow_control` change on its stable Block ID fixed it; the recheck passed
at Revision 7 and the result remained 30 pages. Render times per revision and full
command timings are in the JSON reports. Repair success for that real target is
1/1; this is fixture evidence, not a production-wide success-rate estimate.

Both final structure/layout checks passed. Visual status remains pending for these
standalone CLI artifacts. Background review is separately tested with host-rendered
images and a scripted image-model response, including delayed/stale responses,
identity/revision/fingerprint checks and private ledger application flags. No live
external model was configured for this task. PNGs are representative page samples,
not a claim that every page received a human visual verdict.

The browser evidence uses the actual main Agent runner, native Bubblewrap sandbox,
LibreOffice pagination and a scripted language model: 12 pages, steering during
generation, live SSE and preview, focus/scroll/closed-state preservation, read-only
view and reload recovery. Browser page errors: zero. The measured p95 preview
latency was 4591.15 ms; this environment result is not an SLA.

Reproduce from `agent-runtime` with Python dependencies from the lockfiles, a
sandbox-visible Python runtime, LibreOffice and the fonts used by the fixtures:

```sh
python scripts/benchmark_docx_workflow.py --case academic --sections 8 --paragraphs 7 --page-target 20 --output /tmp/academic
python scripts/benchmark_docx_workflow.py --case academic --sections 8 --paragraphs 7 --page-target 20 --legacy --output /tmp/academic-legacy
python scripts/benchmark_docx_workflow.py --case technical --sections 5 --paragraphs 4 --page-target 30 --output /tmp/technical
PYTHONPATH=. pytest --import-mode=importlib docx-ooxml-skill/tests pptx-ooxml-skill/tests tests
```

Page counts can vary with Office/font versions; page_target stays advisory.
Four unrelated baseline platform assertions had drifted from the already-shipped
file-list API: the owner-scoped global list exists, and per-session entries include
modified_at. They were reproduced on unmodified main and reconciled without changing
production routing or weakening cross-session download/upload isolation assertions.

Validation recorded: full DOCX/PPTX/platform suite **463 passed**; final DOCX
source after restore-chain coverage **64 passed**; Office UI state tests **4 passed**;
frontend production build passed. Restore-chain coverage verifies that restoring a
revision created after an earlier restore retains that snapshot’s plan and legacy
review contract. These are actual executed checks, not inferred pass counts.
