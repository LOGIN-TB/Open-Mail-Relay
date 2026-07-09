<script setup lang="ts">
import { ref, onMounted } from 'vue'
import api from '../../api/client'
import { useApi } from '../../composables/useApi'
import t from '../../i18n/de'

const { call, silent } = useApi()

interface PortalSettings {
  api_key: string
  allowed_ips: string
  api_url: string
  server_hostname: string
  provisioning_enabled: boolean
  sender_maps_enabled: boolean
  quota_enforcement_enabled: boolean
}

const settings = ref<PortalSettings | null>(null)
const saving = ref(false)
const generating = ref(false)

onMounted(async () => {
  // Fehler bewusst ignoriert
  settings.value = await silent(() => api.get<PortalSettings>('/portal-settings'))
})

async function save() {
  if (!settings.value) return
  saving.value = true
  const body = {
    portal_allowed_ips: settings.value.allowed_ips,
    provisioning_enabled: settings.value.provisioning_enabled,
    sender_maps_enabled: settings.value.sender_maps_enabled,
    quota_enforcement_enabled: settings.value.quota_enforcement_enabled,
  }
  const data = await call(
    () => api.put<PortalSettings>('/portal-settings', body),
    { success: t.config.portalSettingsSaved },
  )
  if (data) settings.value = data
  saving.value = false
}

async function generateKey() {
  generating.value = true
  const data = await call(
    () => api.post<PortalSettings>('/portal-settings/generate-key'),
    { success: t.config.portalKeyGenerated },
  )
  if (data) settings.value = data
  generating.value = false
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

      <div class="field full-width">
        <label>{{ t.config.portalProvisioning }}</label>
        <p class="field-hint">{{ t.config.portalProvisioningHint }}</p>
        <label class="toggle-row">
          <input type="checkbox" v-model="settings.provisioning_enabled" />
          <span>{{ settings.provisioning_enabled ? t.config.portalProvisioningOn : t.config.portalProvisioningOff }}</span>
        </label>
      </div>

      <div class="field full-width">
        <label>{{ t.config.senderMaps }}</label>
        <p class="field-hint">{{ t.config.senderMapsHint }}</p>
        <label class="toggle-row">
          <input type="checkbox" v-model="settings.sender_maps_enabled" />
          <span>{{ settings.sender_maps_enabled ? t.config.senderMapsOn : t.config.senderMapsOff }}</span>
        </label>
      </div>

      <div class="field full-width">
        <label>{{ t.config.quotaEnforcement }}</label>
        <p class="field-hint">{{ t.config.quotaEnforcementHint }}</p>
        <label class="toggle-row">
          <input type="checkbox" v-model="settings.quota_enforcement_enabled" />
          <span>{{ settings.quota_enforcement_enabled ? t.config.quotaEnforcementOn : t.config.quotaEnforcementOff }}</span>
        </label>
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

.toggle-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.85rem;
  color: #334155;
  cursor: pointer;
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
