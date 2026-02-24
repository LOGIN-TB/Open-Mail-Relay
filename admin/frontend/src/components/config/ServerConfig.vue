<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import InputText from 'primevue/inputtext'
import Button from 'primevue/button'
import t from '../../i18n/de'

interface StepStatus {
  step: string
  success: boolean
  detail: string
}

const props = defineProps<{
  config: {
    hostname: string
    domain: string
    relay_domains: string
    message_size_limit: number
    mynetworks_count: number
  } | null
  loading: boolean
  saving: boolean
  savingSteps: StepStatus[]
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

const hostnameChanged = computed(() => {
  return props.config != null && hostname.value !== props.config.hostname
})

function save() {
  emit('update', { hostname: hostname.value, domain: domain.value })
}

function formatBytes(bytes: number): string {
  return Math.round(bytes / 1024 / 1024) + ' MB'
}

const stepLabels: Record<string, string> = {
  postfix_reload: t.config.stepPostfixReload,
  caddy_restart: t.config.stepCaddyRestart,
  tls_sync: t.config.stepTlsSync,
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
          <InputText v-model="hostname" class="w-full" :disabled="saving" />
          <small class="hostname-hint" v-if="hostnameChanged">
            <i class="pi pi-info-circle"></i> {{ t.config.hostnameHint }}
          </small>
        </div>
        <div class="field">
          <label>{{ t.config.domain }}</label>
          <InputText v-model="domain" class="w-full" :disabled="saving" />
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

        <!-- Step progress overlay -->
        <div v-if="saving || savingSteps.length > 0" class="steps-progress">
          <div v-for="s in savingSteps" :key="s.step" class="step-row">
            <i v-if="s.success" class="pi pi-check-circle step-icon step-ok"></i>
            <i v-else class="pi pi-times-circle step-icon step-fail"></i>
            <span>{{ stepLabels[s.step] || s.step }}</span>
          </div>
          <div v-if="saving" class="step-row">
            <i class="pi pi-spin pi-spinner step-icon step-pending"></i>
            <span>{{ t.common.loading }}</span>
          </div>
        </div>

        <div class="actions">
          <Button :label="t.config.save" icon="pi pi-save" @click="save" :loading="saving" :disabled="saving" />
          <Button :label="t.config.reload" icon="pi pi-refresh" severity="secondary" @click="emit('reload')" :disabled="saving" />
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

.hostname-hint {
  color: #d97706;
  font-size: 0.8rem;
  display: flex;
  align-items: center;
  gap: 0.35rem;
  margin-top: 0.15rem;
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

.steps-progress {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 0.75rem 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.step-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.85rem;
}

.step-icon {
  font-size: 1rem;
}

.step-ok {
  color: #16a34a;
}

.step-fail {
  color: #dc2626;
}

.step-pending {
  color: #2563eb;
}

.actions {
  display: flex;
  gap: 0.75rem;
  margin-top: 0.5rem;
}
</style>
