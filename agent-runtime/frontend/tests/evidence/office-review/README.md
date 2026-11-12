# Office review browser regression evidence

Real Chromium rendered both shipped Vue frontends. Screenshots use controlled
Office review protocol fixtures and existing real DOCX-rendered PNGs; the model ID
`fixture/vision-model` identifies fixture metadata. These are UI regression
captures, not claims of new live model reviews.

Verified in each frontend: three independent review folds, bound revision/request/
fingerprints, raw metadata and unknown severity, page navigation, verified region
highlight, page-only fallback, running/idle main-Agent delegation, delegate and
retry HTTP failures, unavailable reviews, obsolete request/revision isolation (including request-less accepted events that carry delivery/finalized flags),
preview-not-ready protection, scrolling verified regions into view at width zoom, PPTX element/region highlight and issue dismissal,
and whole-document/whole-deck navigation and delegation. The whole-deck panel
remains open after navigating to a problem page. Delegation never calls human
approval endpoints and never marks an issue resolved.

`*-results.json` records the actual intercepted HTTP paths and artifact contexts.
The existing real FastAPI steering route is covered separately by test_runtime.py;
actual unique PDF/block coordinates by test_cn_quality.py.

Validation: 505 Office/platform Python tests passed; 29 frontend adapter/state/
delegation/parity tests passed; both production builds and both Chromium flows
passed. Reproduce with the commands in ../../OFFICE_REVIEW.md.
