"""Independent deterministic, page visual and document visual delivery states.

This pure projection is used by both CLI delivery and host/UI status. Missing,
unknown, partial and stale evidence is never promoted to a successful review.
"""


def delivery(state):
    revision = state['revision']
    check = state.get('document_check') or {}
    pages = state.get('pages', [])
    modern = state.get('quality_contract', 1) >= 2
    current_final = check.get('revision') == revision and check.get('final')
    checked = current_final and check.get('passed') and (not modern or check.get('collision_check_executed'))
    deterministic = 'passed' if checked else 'failed' if current_final else 'pending'
    request = state.get('visual_request') or {}
    fingerprints = [page['fingerprint'] for page in pages]
    eligible = not modern or (request.get('eligible') and request.get('revision') == revision
                              and request.get('fingerprints') == fingerprints and bool(request.get('request_id')))
    current = []
    for page in pages:
        review = (state.get('aesthetic_reviews') or {}).get(str(page['page'])) or {}
        if (eligible and review.get('revision') == revision and review.get('fingerprint') == page['fingerprint']
                and review.get('request_id') == request.get('request_id')):
            current.append(dict(review, page=page['page']))
    statuses = [review.get('status') for review in current]
    if len(current) < len(pages) or not pages:
        page_status = 'pending'
    elif 'unavailable' in statuses:
        page_status = 'unavailable'
    elif any(status in ('failed', 'uncertain', 'issues') for status in statuses):
        page_status = 'issues'
    else:
        page_status = 'passed' if all(status == 'passed' for status in statuses) else 'pending'
    document = state.get('document_review') or {}
    document_current = (eligible and bool(pages) and document.get('revision') == revision
                        and document.get('fingerprints') == fingerprints
                        and document.get('request_id') == request.get('request_id'))
    document_status = document.get('status', 'pending') if document_current else 'pending'
    if document_status in ('failed', 'uncertain'):
        document_status = 'issues'
    if document_status not in ('passed', 'issues', 'pending', 'unavailable'):
        document_status = 'pending'
    complete = page_status in ('passed', 'issues') and document_status in ('passed', 'issues')
    if deterministic != 'passed':
        status = 'draft_failed_layout' if deterministic == 'failed' else 'draft_pending_check'
    elif 'unavailable' in (page_status, document_status):
        status = 'draft_visual_unavailable'
    elif not complete:
        status = 'draft_pending_visual'
    elif 'issues' in (page_status, document_status):
        status = 'draft_visual_issues'
    else:
        status = 'accepted'
    return dict(status=status, revision=revision, design_id=(state.get('selected_design') or {}).get('id'),
                deterministic=deterministic, page_visual=page_status, document_visual=document_status,
                visual_complete=complete, reviewed_pages=len(current), total_pages=len(pages),
                issue_pages=[review['page'] for review in current if review.get('issues') or review.get('status') in ('failed', 'uncertain', 'issues')],
                repair_attempts=(state.get('repair_summary') or {}).get('attempts', 0),
                repair_stop_reason=(state.get('repair_summary') or {}).get('stop_reason'),
                unresolved=check.get('repair_targets', []), document_review=document if document_current else None)
