<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useSettingsStore } from '../../stores/settings'
import t from '../../i18n/de'

const store = useSettingsStore()
const localTz = ref('Europe/Berlin')
const saved = ref(false)

const timezones = [
  'Europe/Berlin',
  'Europe/Vienna',
  'Europe/Zurich',
  'Europe/Amsterdam',
  'Europe/Brussels',
  'Europe/Paris',
  'Europe/London',
  'Europe/Madrid',
  'Europe/Rome',
  'Europe/Lisbon',
  'Europe/Warsaw',
  'Europe/Prague',
  'Europe/Budapest',
  'Europe/Stockholm',
  'Europe/Copenhagen',
  'Europe/Oslo',
  'Europe/Helsinki',
  'Europe/Athens',
  'Europe/Bucharest',
  'Europe/Istanbul',
  'Europe/Moscow',
  'America/New_York',
  'America/Chicago',
  'America/Denver',
  'America/Los_Angeles',
  'Asia/Tokyo',
  'Asia/Shanghai',
  'UTC',
]

onMounted(() => {
  localTz.value = store.timezone
})

async function save() {
  await store.updateTimezone(localTz.value)
  localTz.value = store.timezone
  saved.value = true
  setTimeout(() => { saved.value = false }, 3000)
}
</script>

<template>
  <div class="card timezone-card">
    <h3>{{ t.config.timezone }}</h3>
    <p class="hint">{{ t.config.timezoneHint }}</p>
    <div class="timezone-fields">
      <label class="field">
        <span>{{ t.config.timezoneLabel }}</span>
        <select v-model="localTz" class="tz-select">
          <option v-for="tz in timezones" :key="tz" :value="tz">{{ tz }}</option>
        </select>
      </label>
      <button class="btn btn-primary" @click="save">{{ t.common.save }}</button>
    </div>
    <div v-if="saved" class="saved-msg">{{ t.config.timezoneSaved }}</div>
  </div>
</template>

<style scoped>
.card {
  background: white;
  border-radius: 12px;
  padding: 1.25rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
  border: 1px solid #e2e8f0;
}

.card h3 {
  font-size: 1rem;
  color: #1e293b;
  margin-bottom: 0.5rem;
}

.hint {
  font-size: 0.8rem;
  color: #64748b;
  margin-bottom: 1rem;
}

.timezone-fields {
  display: flex;
  align-items: flex-end;
  gap: 1rem;
  flex-wrap: wrap;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
  font-size: 0.85rem;
  color: #475569;
}

.tz-select {
  padding: 0.5rem 0.75rem;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  font-size: 0.85rem;
  min-width: 220px;
  background: white;
}

.tz-select:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.15);
}

.btn {
  padding: 0.5rem 1rem;
  border-radius: 8px;
  font-size: 0.85rem;
  font-weight: 600;
  border: none;
  cursor: pointer;
  transition: background 0.15s;
}

.btn-primary {
  background: #3b82f6;
  color: white;
}

.btn-primary:hover {
  background: #2563eb;
}

.saved-msg {
  margin-top: 0.75rem;
  font-size: 0.85rem;
  color: #16a34a;
  font-weight: 600;
}
</style>
