<script setup lang="ts">
import { ref, watch } from 'vue'
import { useToast } from 'primevue/usetoast'
import type { ThrottleConfig } from '../../stores/throttle'
import { useThrottleStore } from '../../stores/throttle'
import t from '../../i18n/de'

const props = defineProps<{
  config: ThrottleConfig | null
}>()

const toast = useToast()
const store = useThrottleStore()
const batchInterval = ref(10)
const saving = ref(false)

watch(() => props.config, (cfg) => {
  if (cfg) {
    batchInterval.value = cfg.batch_interval_minutes
  }
}, { immediate: true })

async function save() {
  saving.value = true
  try {
    await store.updateConfig({ batch_interval_minutes: batchInterval.value })
    toast.add({ severity: 'success', summary: t.common.success, detail: t.throttling.settingsSaved, life: 3000 })
  } catch (e: any) {
    toast.add({ severity: 'error', summary: t.common.error, detail: e.response?.data?.detail ?? 'Fehler', life: 5000 })
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="card">
    <div class="card-header">
      <h3>{{ t.throttling.settings }}</h3>
    </div>
    <div class="card-body">
      <div class="form-group">
        <label>{{ t.throttling.batchInterval }}</label>
        <div class="input-row">
          <input v-model.number="batchInterval" type="number" min="1" max="60" />
          <span class="unit">{{ t.throttling.minutes }}</span>
          <button class="btn btn-primary" :disabled="saving" @click="save">{{ t.common.save }}</button>
        </div>
      </div>
      <div class="info-box">
        <i class="pi pi-info-circle"></i>
        <span>{{ t.throttling.batchInfo }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.card {
  background: white;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
}

.card-header {
  padding: 1rem 1.25rem;
  border-bottom: 1px solid #e2e8f0;
}

.card-header h3 {
  margin: 0;
  font-size: 1.1rem;
  color: #1e293b;
}

.card-body {
  padding: 1.25rem;
}

.form-group label {
  display: block;
  font-size: 0.85rem;
  font-weight: 600;
  color: #475569;
  margin-bottom: 0.5rem;
}

.input-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.input-row input {
  width: 80px;
  padding: 0.5rem 0.75rem;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  font-size: 0.9rem;
}

.unit {
  color: #64748b;
  font-size: 0.85rem;
}

.info-box {
  margin-top: 1rem;
  padding: 0.75rem 1rem;
  background: #eff6ff;
  border-radius: 8px;
  font-size: 0.85rem;
  color: #1e40af;
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
}

.info-box i {
  margin-top: 2px;
  flex-shrink: 0;
}

.btn {
  padding: 0.5rem 1rem;
  border-radius: 6px;
  border: 1px solid #e2e8f0;
  background: white;
  color: #475569;
  cursor: pointer;
  font-size: 0.85rem;
}

.btn-primary {
  background: #3b82f6;
  border-color: #3b82f6;
  color: white;
}

.btn-primary:hover {
  background: #2563eb;
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
</style>
