<script setup lang="ts">
import { ref, watch } from 'vue'
import InputText from 'primevue/inputtext'
import Button from 'primevue/button'
import t from '../../i18n/de'

export interface BanSettingsData {
  max_attempts: number
  time_window_minutes: number
  ban_durations: number[]
}

const props = defineProps<{
  settings: BanSettingsData
}>()

const emit = defineEmits<{
  save: [settings: BanSettingsData]
}>()

const maxAttempts = ref(String(props.settings.max_attempts))
const timeWindow = ref(String(props.settings.time_window_minutes))
const durationsText = ref(props.settings.ban_durations.join(', '))

watch(() => props.settings, (s) => {
  maxAttempts.value = String(s.max_attempts)
  timeWindow.value = String(s.time_window_minutes)
  durationsText.value = s.ban_durations.join(', ')
})

function save() {
  const durations = durationsText.value
    .split(',')
    .map((s) => parseInt(s.trim(), 10))
    .filter((n) => !isNaN(n) && n > 0)

  emit('save', {
    max_attempts: parseInt(maxAttempts.value, 10) || 5,
    time_window_minutes: parseInt(timeWindow.value, 10) || 10,
    ban_durations: durations,
  })
}
</script>

<template>
  <div class="card">
    <h3>{{ t.ipBans.settings }}</h3>
    <form @submit.prevent="save" class="settings-form">
      <div class="field-row">
        <div class="field">
          <label>{{ t.ipBans.maxAttempts }}</label>
          <InputText v-model="maxAttempts" type="number" min="1" class="w-full" />
        </div>
        <div class="field">
          <label>{{ t.ipBans.timeWindow }}</label>
          <InputText v-model="timeWindow" type="number" min="1" class="w-full" />
        </div>
      </div>
      <div class="field">
        <label>{{ t.ipBans.banDurations }}</label>
        <InputText v-model="durationsText" :placeholder="t.ipBans.banDurationsPlaceholder" class="w-full" />
        <small class="hint">{{ t.ipBans.banDurationsHint }}</small>
      </div>
      <div class="actions">
        <Button type="submit" :label="t.common.save" icon="pi pi-check" />
      </div>
    </form>
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
  margin-bottom: 1rem;
}

.settings-form {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.field-row {
  display: flex;
  gap: 1rem;
}

.field-row .field {
  flex: 1;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
}

.field label {
  font-size: 0.85rem;
  font-weight: 600;
  color: #475569;
}

.hint {
  font-size: 0.75rem;
  color: #94a3b8;
}

.w-full {
  width: 100%;
}

.actions {
  display: flex;
  gap: 0.75rem;
}
</style>
