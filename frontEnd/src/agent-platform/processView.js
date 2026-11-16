import { rawText } from './conversation.js'
export function stepBody(step, t) {
  if (step.kind === 'compaction') {
    const sections = []
    const outcome = step.compactionStatus || (step.status === 'running' ? 'running' : 'compacted')
    const outcomeKey = `process.compaction.${outcome}`
    sections.push(t(outcomeKey) !== outcomeKey ? t(outcomeKey) : t('process.compaction.compacted'))
    if (step.usedTokens != null && step.windowTokens != null && step.windowTokens > 0) {
      sections.push(t('process.compaction.tokens', { used: step.usedTokens, window: step.windowTokens }))
    }
    if (step.content) sections.push(step.content)
    return sections.join('\n\n')
  }
  if (step.kind !== 'tool') return step.content || t('process.waitingSummary')
  const sections = []
  if (step.arguments != null) sections.push(`${t('process.input')}\n${rawText(step.arguments)}`)
  if (step.streamedOutput) {
    let output = step.streamedOutput
    if (step.streams?.some(chunk => chunk.stream === 'stderr')) {
      let previous
      output = step.streams.map(chunk => {
        const prefix = chunk.stream !== previous ? `${previous ? '\n' : ''}[${chunk.stream}]\n` : ''
        previous = chunk.stream
        return prefix + chunk.content
      }).join('')
    }
    sections.push(`${t('process.output')}\n${output}`)
  }
  if (step.finalOutput && step.finalOutput !== step.streamedOutput) sections.push(`${t('process.result')}\n${step.finalOutput}`)
  return sections.join('\n\n') || t('process.waitingOutput')
}
export function elapsed(start, end, duration, now, live = true) {
  if (duration != null) return duration
  return start == null || (!live && end == null) ? null : Math.max(0, (end ?? now) - start)
}
export function formatDuration(ms, t) {
  if (ms == null || !Number.isFinite(ms)) return t('process.durationUnknown')
  const seconds = ms / 1000
  if (seconds < 60) return t('process.seconds', { seconds: seconds.toFixed(1) })
  const minutes = Math.floor(seconds / 60), rest = Math.floor(seconds % 60)
  return t('process.minutesSeconds', { minutes, seconds: rest })
}
