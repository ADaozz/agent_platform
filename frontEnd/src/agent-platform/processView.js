import { rawText } from './conversation.js'

const fileTools = new Set(['read_file', 'write_file', 'edit_file', 'delete', 'ls'])
const textSummaryArgument = new Map([['execute', 'command'], ['web_search', 'query'], ['web_fetch', 'url']])
const fileName = path => path.replace(/[\\/]+$/, '').split(/[\\/]/).at(-1) || path
const platformDataBoundary = /\/\.platform(?:-[\w-]+)?(?=\/|$)|(?=\/workspaces\/ws_[a-f0-9]{32}\b)/

function shortenCommandPaths(command) {
  return command
    .replace(/\$(?:PLATFORM_DATA_DIR\b|\{PLATFORM_DATA_DIR\})/g, '~/···')
    .replace(/(^|[\s"'=;&|()<>\x60])(\/(?!\/)[^\s"';&|()<>\x60]+)/g, (match, separator, path) => {
      const boundary = platformDataBoundary.exec(path)
      return boundary ? separator + '~/···' + path.slice(boundary.index + boundary[0].length) : match
    })
}

function lineCount(text) {
  const lines = text.split(/\r\n|[\r\n\v\f\u001c-\u001e\u0085\u2028\u2029]/)
  return lines.length - (lines.at(-1) === '' ? 1 : 0)
}

export function compactToolSummary(step, t) {
  if (step.kind !== 'tool') return null
  const args = step.arguments || {}
  const textArgument = textSummaryArgument.get(step.name)
  if (textArgument) {
    const value = args[textArgument]
    const command = step.name === 'execute'
    const text = typeof value === 'string' ? value.trim().replace(/\r\n|[\r\n]/g, ' ') : ''
    return { text: command ? shortenCommandPaths(text) : text, command }
  }
  if (!fileTools.has(step.name)) return null
  const argument = step.name === 'ls' ? args.path : args.file_path
  const path = typeof argument === 'string' ? argument : ''
  const summary = { text: fileName(path), title: path }
  if (step.status !== 'completed' || step.name === 'delete') return summary
  const file = step.artifact?.file_summary
  if (step.name === 'ls') {
    if (!Array.isArray(file?.entries)) {
      return step.finalOutput === 'No files found' ? { text: t('process.emptyListing'), title: path } : summary
    }
    const names = file.entries.map(entry => fileName(entry) + (entry.endsWith('/') && entry !== '/' ? '/' : ''))
    const remaining = Number.isSafeInteger(file.total) ? file.total - names.length : 0
    return {
      text: names.join(', ') || t('process.emptyListing'),
      title: file.entries.join('\n') || path,
      more: remaining > 0 ? t('process.moreFiles', { n: remaining }) : file.total === null ? '…' : '',
    }
  }
  if (step.name === 'read_file') return summary
  if (file) {
    if (Number.isSafeInteger(file.removed) && file.removed > 0) summary.removed = file.removed
    if (Number.isSafeInteger(file.added) && file.added > 0) summary.added = file.added
  } else if (step.name === 'write_file' && step.artifact?.operation === 'create' &&
      typeof args.content === 'string' && !args.content.includes('\0')) {
    summary.added = lineCount(args.content)
  }
  return summary
}

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
  const args = step.arguments
  if (args != null) {
    const displayArgs = step.name === 'execute' && typeof args.command === 'string'
      ? { ...args, command: shortenCommandPaths(args.command) }
      : args
    sections.push(`${t('process.input')}\n${rawText(displayArgs)}`)
  }
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
