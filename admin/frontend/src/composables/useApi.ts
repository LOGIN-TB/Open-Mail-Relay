import { useToast } from 'primevue/usetoast'
import t from '../i18n/de'

/** Extract the backend error detail from an axios error, with fallback. */
export function apiErrorDetail(e: unknown, fallback = 'Fehler'): string {
  if (typeof e === 'object' && e !== null) {
    const detail = (e as { response?: { data?: { detail?: unknown } } }).response?.data?.detail
    if (typeof detail === 'string' && detail) return detail
  }
  return fallback
}

/**
 * Zentrale Fehlerbehandlung fuer API-Aufrufe.
 *
 * `call`   — fuehrt den Aufruf aus, zeigt bei Fehler einen Error-Toast
 *            (und optional bei Erfolg einen Success-Toast), gibt die
 *            Response-Daten oder `null` zurueck.
 * `silent` — wie `call`, aber ohne Toasts (fuer Dashboard-Polling).
 */
export function useApi() {
  const toast = useToast()

  async function call<T>(
    fn: () => Promise<{ data: T }>,
    opts?: { success?: string; error?: string },
  ): Promise<T | null> {
    try {
      const { data } = await fn()
      if (opts?.success) {
        toast.add({ severity: 'success', summary: t.common.success, detail: opts.success, life: 3000 })
      }
      return data
    } catch (e) {
      toast.add({
        severity: 'error',
        summary: t.common.error,
        detail: apiErrorDetail(e, opts?.error ?? 'Fehler'),
        life: 5000,
      })
      return null
    }
  }

  async function silent<T>(fn: () => Promise<{ data: T }>): Promise<T | null> {
    try {
      const { data } = await fn()
      return data
    } catch {
      return null
    }
  }

  return { call, silent }
}
