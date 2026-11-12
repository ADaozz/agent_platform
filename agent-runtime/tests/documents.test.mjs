import test from 'node:test'
import assert from 'node:assert/strict'
import { mergeDocument } from '../../frontEnd/src/agent-platform/features/docx/state.js'
test('late snapshots and events never replace a newer revision', () => {
  const newest = mergeDocument(null, { document_id: 'report', revision: 7, pages: [] })
  assert.equal(mergeDocument(newest, { document_id: 'report', revision: 6 }), newest)
})
test('new commits invalidate old page reviews; same-version reviews merge', () => {
  const reviewed = { document_id: 'report', revision: 7, finalized: true, pages: [{ page: 1, status: 'passed' }] }
  const update = mergeDocument(reviewed, { document_id: 'report', revision: 8 })
  assert.deepEqual(update.pages, [])
  assert.equal(update.finalized, false)
  const review = mergeDocument(update, { document_id: 'report', revision: 8, pages: [{ page: 1, status: 'pending' }] })
  assert.equal(review.pages[0].status, 'pending')
})

test('a document rebuilt from scratch replaces the previous revision history', () => {
  const old = mergeDocument(null, {document_id: 'doc', revision: 13, pages: [{page: 1}]})
  // Untagged older events cannot move a document backwards.
  assert.equal(mergeDocument(old, {document_id: 'doc', revision: 2}).revision, 13)
  const rebuilt = mergeDocument(old, {document_id: 'doc', revision: 0, history_id: 'h2'})
  assert.equal(rebuilt.revision, 0)
  assert.deepEqual(rebuilt.pages, [])
  const next = mergeDocument(rebuilt, {document_id: 'doc', revision: 1, history_id: 'h2'})
  assert.equal(next.revision, 1)
  // Within one identified history the revision fence still holds.
  assert.equal(mergeDocument(next, {document_id: 'doc', revision: 0, history_id: 'h2'}).revision, 1)
  assert.equal(mergeDocument(next, {document_id: 'doc', revision: 0, history_id: 'h3'}).revision, 0)
})
