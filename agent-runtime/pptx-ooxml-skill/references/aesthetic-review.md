# Visual (aesthetic) review by the main Agent

The deterministic checks prove that a slide is intact; they cannot judge composition. That judgement comes from the main Agent itself looking at the real Impress render. No other model or external API is called, on the platform or in standalone use. The review is advice: it never blocks building or delivering the deck, and the Agent changes nothing because of it unless the user asks.

## Flow

Finish the whole deck → `check-deck` → local deterministic overlap repair and recheck while progress continues → `review-images` → open every slide image with `read_file` → `submit-review` → suggestions only.

1. At the end of generation, `check-deck` uses the page checker to store `technical_review`, `visual_integrity` and `aesthetic_review: pending` (`reason: awaiting_agent_review`). A slide with deterministic errors is `blocked` and cannot be reviewed. With two or more slides it also opens a deck review request.
2. `review-images files/deck.pptx [--slide-id …]` renders the current revision (cached), checks that every slide still has the pixels its check recorded, and returns per slide `image` (absolute PNG path), `reviewable`, `reason` and `status`, plus `deck.sheet` (numbered contact sheet of all slides), `guidance` (rules and dimensions), `context_file` and a `submit` template. A slide that changed since its check, failed its checks, or contains a native chart LibreOffice cannot draw reliably is not reviewable.
3. Open each image with `read_file`. `context_file` holds, per slide, the design profile, selected_design (style MD, actual parameters, user overrides), layout and page purpose (`--intent`), user layout constraints (`--constraint`), the native element manifest (IDs, types, text, geometry, styles), chart data, diagram nodes and edges with their bindings, and the automatic findings. It maps observations to element IDs; it never replaces looking at the image.
4. Submit with `submit-review files/deck.pptx --request tmp/visual-review.json`. The request names the current `revision`; slides and the deck review can be sent together or in batches. Every entry is validated first; if any entry is malformed the whole request is rejected and nothing is recorded. The result is applied only if the slide's check is still the current one; a later submission for the same check replaces the earlier one.
5. `review-status [--slide-id …]` returns the result, critical issues and suggestions separately, and the next action.

If the current model cannot read images, submit `{"slide_id":"…","unavailable":"reason"}` (or `"deck":{"unavailable":"reason"}`); the review becomes `unavailable`, never a pass.

## Dimensions

composition, focal_point, hierarchy, legibility, spacing, chart_quality, diagram_semantics, media_balance, decoration, profile_consistency, templating. Every dimension needs a verdict (`ok` / `issue` / `not_applicable` / `uncertain`) and concrete evidence that points at visible content. For diagrams, compare the visible lines with the declared edges; a relation you cannot confirm is `needs_verification` and low confidence, never assumed correct.

Style precedence: the user's explicit requirements and adjustments, then the deck's actual parameters, then the style MD. Undeclared colours, sizes or margins are not requirements; an edited existing deck keeps its own visual system.

## Submission

```json
{"revision":7,"slides":[{"slide_id":"s3","review":{"status":"fail","summary":"存在无意义的连接线",
 "checks":{"composition":{"verdict":"ok","evidence":"…"},"focal_point":{"verdict":"ok","evidence":"…"}},
 "issues":[{"id":"visual-001","category":"diagram_semantics","severity":"major","element_ids":["connector-01"],
   "region":[0.38,0.42,0.12,0.10],"observation":"连接线未明确连接两个节点","reason":"无法判断具体依赖关系",
   "suggestion":"绑定正确节点或删除装饰线","confidence":"high","needs_verification":false}]}}],
 "deck":{"review":{"status":"pass","summary":"…","checks":{"design_system":{"verdict":"ok","evidence":"…"}},"issues":[]}}}
```

`checks` must contain every dimension (the example is shortened). `region` is normalised `[x, y, w, h]` of the image. Issue IDs are `visual-001…` for slides and `deck-001…` for the deck. Element IDs not in the manifest are moved to `unmapped_element_ids` and flagged; the region stays as the locator.

## Status rules

| status | when |
| --- | --- |
| `failed` | at least one `critical`/`major` issue with medium/high confidence and no pending verification, whatever the submitted verdict; all findings remain advice |
| `uncertain` | a `critical`/`major` issue that is low-confidence or needs verification; the verdict is uncertain; any dimension is uncertain; or the verdict is fail without a confirmed blocking issue |
| `passed` | none of the above; `minor` issues remain as optional suggestions |
| `unavailable` | the Agent could not view the images |
| `pending` | requested, not submitted yet |

A generous-whitespace minimal page with a clear focal point is not a defect. A layout the user explicitly asked to keep (`--constraint`) is an accepted decision; readability and data correctness are still checked.

## Persistence

Each applied review is stored in the presentation state with a generated `review_id`, `reviewer: main_agent`, `prompt_version` (guidance version), revision, slide fingerprint, render and pixel hashes and `reviewed_at`. On the platform the host also copies every submitted review from the event journal into a host-private ledger (`<session>/artifact-review/…/vision-reviews.sqlite`).

## Repair policy and delivery

- Only deterministic overlap findings trigger autonomous repairs. Edit listed slide/element IDs in the existing PPT, then re-render and repeat `check-deck`. There is no fixed round cap: continue while `repair_control.autonomous_repair_allowed` is true. Shared Office progress detection stops on unchanged content, repeated errors, stationary/worsening geometry or a repair cycle. Report the stop reason and unresolved issues and retain the editable draft. Never regenerate unrelated pages, restart a stopped loop without a real correction, or silently suppress errors.
- All visual findings are advice, including critical ones. Reviews carry `auto_repair: false, advisory_only: true`. Only a user repair request authorizes edits based on these suggestions.
- A slide shows `needs_attention` only while a critical finding is open. That status is informational.
- Slide creation/import/clone has no intermediate check gate, including strict mode. Check after the whole deck is ready.
- `finalize` needs automatic and content checks per slide. Visual review, deck review, `uncertain` and `unavailable` never block it; the finalize event lists outstanding critical findings and suggestion counts for the delivery message. On the platform the host then checks that every claimed verdict was really submitted through `submit-review` and publishes `finalize_verified`.
- There is no human accept or reject UI/API. Issue dismissal and sending a suggestion to the Agent remain; dismissal never converts a verdict into acceptance.

## Deck review

`check-deck` opens the deck review automatically; `request-deck-review --base-revision N` (all slides checked) opens a fresh one, for example after the user asks for another look. Review the numbered `deck.sheet` for cross-slide issues only: design_system, transitions, repetition, card_overuse, consistency, density_rhythm, bookends. Every issue must name 1–6 concrete pages; issues covering most of a 5+ page deck or pages outside it are rejected and listed separately. Any new revision makes the deck review stale. Deck findings are suggestions for the user and never block delivery.
