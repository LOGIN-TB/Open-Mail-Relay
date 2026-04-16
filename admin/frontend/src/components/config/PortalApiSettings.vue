<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useToast } from 'primevue/usetoast'
import api from '../../api/client'
import t from '../../i18n/de'

const toast = useToast()

interface PortalSettings {
  api_key: string
  allowed_ips: string
  api_url: string
  server_hostname: string
}

const settings = ref<PortalSettings | null>(null)
const saving = ref(false)
const generating = ref(false)

onMounted(async () => {
  try {
    const { data } = await api.get('/portal-settings')
    settings.value = data
  } catch {
    // ignore
  }
})

async function save() {
  if (!settings.value) return
  saving.value = true
  try {
    const { data } = await api.put('/portal-settings', {
      portal_allowed_ips: settings.value.allowed_ips,
    })
    settings.value = data
    toast.add({ severity: 'success', summary: t.common.success, detail: t.config.portalSettingsSaved, life: 3000 })
  } catch (e: any) {
    toast.add({ severity: 'error', summary: t.common.error, detail: e.response?.data?.detail ?? 'Fehler', life: 5000 })
  } finally {
    saving.value = false
  }
}

async function generateKey() {
  generating.value = true
  try {
    const { data } = await api.post('/portal-settings/generate-key')
    settings.value = data
    toast.add({ severity: 'success', summary: t.common.success, detail: t.config.portalKeyGenerated, life: 3000 })
  } catch (e: any) {
    toast.add({ severity: 'error', summary: t.common.error, detail: e.response?.data?.detail ?? 'Fehler', life: 5000 })
  } finally {
    generating.value = false
  }
}

</script>

<template>
  <div class="card" v-if="settings">
    <h3>{{ t.config.portalApi }}</h3>
    <p class="hint">{{ t.config.portalApiHint }}</p>

    <div class="fields-grid">
      <div class="field full-width">
        <label>{{ t.config.portalApiKey }}</label>
        <p class="field-hint">{{ t.config.portalApiKeyHint }}</p>
        <div class="key-row">
          <input
            type="text"
            :value="settings.api_key || t.config.portalNoKey"
            readonly
            class="input mono"
            :class="{ disabled: !settings.api_key }"
          />
          <button class="btn btn-secondary" :disabled="generating" @click="generateKey">
            <i class="pi pi-refresh"></i> {{ generating ? t.common.loading : t.config.portalGenerateKey }}
          </button>
        </div>
      </div>

      <div class="field full-width">
        <label>{{ t.config.portalAllowedIps }}</label>
        <p class="field-hint">{{ t.config.portalAllowedIpsHint }}</p>
        <input
          type="text"
          v-model="settings.allowed_ips"
          class="input"
          placeholder="z.B. 203.0.113.50, 198.51.100.10"
        />
      </div>
    </div>

    <div class="actions">
      <button class="btn btn-primary" :disabled="saving" @click="save">
        <i class="pi pi-save"></i> {{ saving ? t.common.loading : t.config.save }}
      </button>
    </div>
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
  font-weight: 600;
  color: #1e293b;
  margin-bottom: 0.25rem;
}

.hint {
  font-size: 0.82rem;
  color: #64748b;
  margin-bottom: 1.25rem;
}

.fields-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}

@media (max-width: 600px) {
  .fields-grid {
    grid-template-columns: 1fr;
  }
}

.field {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
}

.full-width {
  grid-column: 1 / -1;
}

.field label {
  font-size: 0.82rem;
  font-weight: 600;
  color: #475569;
}

.field-hint {
  font-size: 0.78rem;
  color: #94a3b8;
  margin: 0;
}

.input {
  padding: 0.5rem 0.75rem;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  font-size: 0.85rem;
  background: white;
  color: #334155;
  font-family: inherit;
}

.input:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.15);
}

.input.disabled {
  background: #f8fafc;
  color: #94a3b8;
  cursor: not-allowed;
}

.input.mono {
  font-family: 'SF Mono', 'Fira Code', 'Fira Mono', monospace;
  font-size: 0.8rem;
  letter-spacing: -0.02em;
}

.key-row {
  display: flex;
  gap: 0.5rem;
  align-items: stretch;
}

.key-row .input {
  flex: 1;
}

.actions {
  display: flex;
  gap: 0.75rem;
  margin-top: 1.25rem;
}

.btn {
  padding: 0.5rem 1rem;
  border-radius: 8px;
  font-size: 0.85rem;
  font-weight: 600;
  border: none;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  transition: background 0.15s;
  white-space: nowrap;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-primary {
  background: #3b82f6;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: #2563eb;
}

.btn-secondary {
  background: #f1f5f9;
  color: #475569;
}

.btn-secondary:hover:not(:disabled) {
  background: #e2e8f0;
}

</style>
