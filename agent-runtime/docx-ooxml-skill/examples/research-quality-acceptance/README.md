# Research quality workflow acceptance

This is synthetic software-test content, not a submitted research paper or a claim
of institutional/GB/T compliance. The editable DOCX retains native equations,
charts/workbooks, TOC/cross-reference fields and a 60-row table.

- Actual LibreOffice pagination: **23 pages**, revision **14**.
- Design: `cn-engineering-thesis`; Chinese/Latin fonts configured separately.
- Injected defects: cover date pushed to a second page, and empty/stale TOC page results.
- Two local repair revisions followed by real re-render/recheck. The final
  deterministic check, including glyph/image/vector geometry, passed with no targets.
- Actual `deepseek-flash` host service: **23 page-image calls + 1 independent
  whole-document thumbnail review**. Both completed with **Issues**. All advice
  is preserved; the file is correctly **draft_visual_issues**, never finalized.
- Background queue returned in 23.436 ms; complete review took 343.706 s. The
  whole-document review took 96.682 s. These are measured provider/runtime timings.
- 97 submitted atomic operations. Recorded authoring/check/delivery calls: 18,
  versus 133 under the exact old apply-one/checkpoint-per-three protocol: **86.47%**
  fewer main-Agent calls. The old count is protocol-derived; this run does not
  claim a second live legacy execution. Model calls are separate background work.
- `acceptance.json` contains per-page findings, fingerprints, model/prompt IDs,
  request binding, repair counts, delivery status and individual command timings.
  `deterministic-check.json` contains the final geometry/block/section mapping.

The model reported missing page furniture, inconsistent language/heading/caption
choices, sparse pages and table presentation issues in the synthetic fixture.
These are real review results, not filtered failures. Visual advice does not edit
necessary content or trigger a global font reduction. The small reference styles
are generic defaults; institutional templates and official requirements take priority.

Reproduce from repository root (renderer, CJK fonts and runtime dependencies needed):

```sh
python agent-runtime/scripts/accept_docx_research.py --output /tmp/research-quality --live
```

The key is prompted without echo and is never written to evidence. Without a model,
both visual states truthfully become Unavailable. `--review-existing --live` retries
visual review of an existing run using a new request ID; old jobs cannot overwrite it.
