<script setup lang="ts">
import { ref, watch } from 'vue'
import InputText from 'primevue/inputtext'
import Button from 'primevue/button'
import t from '../../i18n/de'

const props = defineProps<{
  config: {
    hostname: string
    domain: string
    relay_domains: string
    message_size_limit: number
    mynetworks_count: number
  } | null
  loading: boolean
}>()

const emit = defineEmits<{
  update: [data: { hostname?: string; domain?: string }]
  reload: []
}>()

const hostname = ref('')
const domain = ref('')

watch(() => props.config, (val) => {
  if (val) {
    hostname.value = val.hostname
    domain.value = val.domain
  }
}, { immediate: true })

function save() {
  emit('update', { hostname: hostname.value, domain: domain.value })
}

function formatBytes(bytes: number): string {
  return Math.round(bytes / 1024 / 1024) + ' MB'
}
</script>

<template>
  <div class="card">
    <h3>{{ t.config.title }}</h3>

    <div v-if="loading" class="loading">{{ t.common.loading }}</div>
    <template v-else-if="config">
      <div class="config-form">
        <div class="field">
          <label>{{ t.config.hostname }}</label>
          <InputText v-model="hostname" class="w-full" />
        </div>
        <div class="field">
          <label>{{ t.config.domain }}</label>
          <InputText v-model="domain" class="w-full" />
        </div>
        <div class="info-row">
          <span class="info-label">{{ t.config.relayDomains }}:</span>
          <code>{{ config.relay_domains }}</code>
        </div>
        <div class="info-row">
          <span class="info-label">{{ t.config.messageSize }}:</span>
          <span>{{ formatBytes(config.message_size_limit) }}</span>
        </div>
        <div class="info-row">
          <span class="info-label">{{ t.config.networksCount }}:</span>
          <span>{{ config.mynetworks_count }}</span>
        </div>
        <div class="actions">
          <Button :label="t.config.save" icon="pi pi-save" @click="save" />
          <Button :label="t.config.reload" icon="pi pi-refresh" severity="secondary" @click="emit('reload')" />
        </div>
      </div>
    </template>
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

.loading {
  text-align: center;
  padding: 2rem;
  color: #94a3b8;
}

.config-form {
  display: flex;
  flex-direction: column;
  gap: 1rem;
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

.w-full {
  width: 100%;
}

.info-row {
  display: flex;
  justify-content: space-between;
  padding: 0.5rem 0;
  border-bottom: 1px solid #f1f5f9;
  font-size: 0.9rem;
}

.info-label {
  color: #64748b;
}

.actions {
  display: flex;
  gap: 0.75rem;
  margin-top: 0.5rem;
}
</style>
