import { useSettingsStore } from '../stores/settings'

export function formatDateTime(ts: string | null): string {
  if (!ts) return '-'
  const store = useSettingsStore()
  return new Date(ts).toLocaleString('de-DE', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    timeZone: store.timezone,
  })
}

export function formatDateTimeShort(ts: string | null): string {
  if (!ts) return '-'
  const store = useSettingsStore()
  return new Date(ts).toLocaleString('de-DE', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    timeZone: store.timezone,
  })
}

export function formatTimeShort(ts: string | null): string {
  if (!ts) return '-'
  const store = useSettingsStore()
  return new Date(ts).toLocaleString('de-DE', {
    day: '2-digit',
    month: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    timeZone: store.timezone,
  })
}
