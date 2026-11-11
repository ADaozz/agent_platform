import messages from './messages.json'
// Embedded in ITAM: theme and locale are the platform-wide preferences toggled in the ITAM header.
import { locale, theme, toggleLocale, toggleTheme } from '@/composables/preferences'

export { locale, theme, toggleLocale, toggleTheme }

export function t(key, values = {}) {
  const message = messages[key]?.[locale.value] || key
  return message.replace(/\{(\w+)\}/g, (match, name) => values[name] ?? match)
}
