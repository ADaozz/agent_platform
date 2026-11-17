import test from 'node:test'
import assert from 'node:assert/strict'
import { relativeCreation, creationDate, taskDuration, taskCost } from '../../frontEnd/src/agent-platform/sessionCard.js'
process.env.TZ = 'UTC'
const now = Date.parse('2026-11-17T12:00:00Z')
const ago = seconds => new Date(now - seconds * 1000).toISOString()
for (const [seconds, en, zh] of [
  [0, 'just now', '刚刚'], [9, 'just now', '刚刚'], [10, '10s ago', '10 秒前'], [59, '59s ago', '59 秒前'],
  [60, '1 min ago', '1 分钟前'], [3599, '59 min ago', '59 分钟前'],
  [3600, '1 hour ago', '1 小时前'], [10800, '3 hours ago', '3 小时前'], [86399, '23 hours ago', '23 小时前'],
  [86400, '1 day ago', '1 天前'], [6 * 86400, '6 days ago', '6 天前'], [7 * 86400, '7 days ago', '7 天前'],
  [29 * 86400, '29 days ago', '29 天前'], [30 * 86400, 'Oct 18, 2026', '2026年10月18日'],
]) test(`relative creation threshold ${seconds}s`, () => {
  assert.equal(relativeCreation(ago(seconds), 'en', now), en)
  assert.equal(relativeCreation(ago(seconds), 'zh', now), zh)
})
test('absolute years, invalid values and future clock skew', () => {
  assert.equal(relativeCreation('2025-10-18T12:00:00Z', 'en', now), 'Oct 18, 2025')
  assert.equal(creationDate('2025-10-18T12:00:00Z', 'zh'), '2025年10月18日')
  assert.equal(relativeCreation('bad-date', 'en', now), '—')
  assert.equal(relativeCreation(ago(-5), 'en', now), 'just now')
})
test('execution duration increases only while running', () => {
  const value = {task_duration_ms: 65000, task_running_since: ago(10), status: 'running'}
  assert.equal(taskDuration(value, 'en', now), '1m 15s')
  assert.equal(taskDuration({...value, status:'waiting_human'}, 'zh', now), '1 分 5 秒')
  assert.equal(taskDuration({task_duration_ms: 3665000}, 'en', now), '1h 1m')
  assert.equal(taskDuration({task_duration_ms: null}, 'en', now), '—')
})
test('cost preserves small charges and missing values', () => {
  assert.equal(taskCost({task_cost_cny: 0}, 'en'), '¥0.00')
  assert.equal(taskCost({task_cost_cny: 0.0042}, 'zh'), '¥0.0042')
  assert.equal(taskCost({task_cost_cny: 1.23}, 'en'), '¥1.23')
  assert.equal(taskCost({task_cost_cny: null}, 'en'), '—')
})
