import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '../api/client'

export const useSettingsStore = defineStore('settings', () => {
  const timezone = ref('Europe/Berlin')

  async function fetchTimezone() {
    try {
      const { data } = await api.get('/config/timezone')
      timezone.value = data.timezone
    } catch {
      // keep default
    }
  }

  async function updateTimezone(tz: string) {
    const { data } = await api.put('/config/timezone', { timezone: tz })
    timezone.value = data.timezone
  }

  return { timezone, fetchTimezone, updateTimezone }
})
