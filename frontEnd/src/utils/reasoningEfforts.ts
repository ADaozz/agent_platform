/** Display order only: configuration order also determines the runtime default. */
const ORDER = ['none', 'minimal', 'low', 'medium', 'high', 'xhigh', 'max']
export function sortReasoningEfforts(values: readonly string[]): string[] {
  return [...values].sort((a, b) => {
    const rank = (value: string) => {
      const index = ORDER.indexOf(value.toLowerCase())
      return index < 0 ? ORDER.length : index
    }
    return rank(a) - rank(b)
  })
}
