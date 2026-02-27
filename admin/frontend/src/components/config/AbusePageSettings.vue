<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useToast } from 'primevue/usetoast'
import api from '../../api/client'
import t from '../../i18n/de'

const toast = useToast()

interface AbuseSettings {
  abuse_email: string
  postmaster_email: string
  abuse_responsible: string
  abuse_phone: string
  abuse_imprint_url: string
  abuse_data_retention: string
  abuse_spam_filtering: string
  abuse_rfc2142: string
  abuse_data_retention_en: string
  abuse_spam_filtering_en: string
  abuse_rfc2142_en: string
  hostname: string
  domain: string
}

const settings = ref<AbuseSettings | null>(null)
const saving = ref(false)

onMounted(async () => {
  try {
    const { data } = await api.get('/abuse-settings')
    settings.value = data
  } catch {
    // ignore – fields stay empty
  }
})

async function save() {
  if (!settings.value) return
  saving.value = true
  try {
    const { abuse_email, postmaster_email, abuse_responsible, abuse_phone,
            abuse_imprint_url, abuse_data_retention, abuse_spam_filtering, abuse_rfc2142,
            abuse_data_retention_en, abuse_spam_filtering_en, abuse_rfc2142_en } = settings.value
    const { data } = await api.put('/abuse-settings', {
      abuse_email, postmaster_email, abuse_responsible, abuse_phone,
      abuse_imprint_url, abuse_data_retention, abuse_spam_filtering, abuse_rfc2142,
      abuse_data_retention_en, abuse_spam_filtering_en, abuse_rfc2142_en,
    })
    settings.value = data
    toast.add({ severity: 'success', summary: t.common.success, detail: t.config.abusePageSaved, life: 3000 })
  } catch (e: any) {
    toast.add({ severity: 'error', summary: t.common.error, detail: e.response?.data?.detail ?? 'Fehler', life: 5000 })
  } finally {
    saving.value = false
  }
}

function openPreview() {
  if (settings.value?.hostname) {
    window.open(`https://${settings.value.hostname}`, '_blank')
  }
}
</script>

<template>
  <div class="card" v-if="settings">
    <h3>{{ t.config.abusePage }}</h3>
    <p class="hint">{{ t.config.abusePageHint }}</p>

    <div class="fields-grid">
      <div class="field">
        <label>{{ t.config.abuseHostname }}</label>
        <input type="text" :value="settings.hostname" disabled class="input disabled" />
      </div>
      <div class="field">
        <label>{{ t.config.abuseDomain }}</label>
        <input type="text" :value="settings.domain" disabled class="input disabled" />
      </div>

      <div class="field">
        <label>{{ t.config.abuseEmail }}</label>
        <input type="email" v-model="settings.abuse_email" class="input" />
      </div>
      <div class="field">
        <label>{{ t.config.postmasterEmail }}</label>
        <input type="email" v-model="settings.postmaster_email" class="input" />
      </div>

      <div class="field">
        <label>{{ t.config.abuseResponsible }}</label>
        <input type="text" v-model="settings.abuse_responsible" class="input" placeholder="z.B. Firma GmbH, Musterstadt" />
      </div>
      <div class="field">
        <label>{{ t.config.abusePhone }}</label>
        <input type="text" v-model="settings.abuse_phone" class="input" placeholder="z.B. +49 611 123456" />
      </div>

      <div class="field full-width">
        <label>{{ t.config.abuseImprintUrl }}</label>
        <input type="url" v-model="settings.abuse_imprint_url" class="input" placeholder="https://www.example.de/impressum" />
      </div>

      <div class="field">
        <label>{{ t.config.abuseDataRetention }} (DE)</label>
        <textarea v-model="settings.abuse_data_retention" class="input textarea" rows="2"></textarea>
      </div>
      <div class="field">
        <label>{{ t.config.abuseDataRetention }} (EN)</label>
        <textarea v-model="settings.abuse_data_retention_en" class="input textarea" rows="2"></textarea>
      </div>
      <div class="field">
        <label>{{ t.config.abuseSpamFiltering }} (DE)</label>
        <textarea v-model="settings.abuse_spam_filtering" class="input textarea" rows="2"></textarea>
      </div>
      <div class="field">
        <label>{{ t.config.abuseSpamFiltering }} (EN)</label>
        <textarea v-model="settings.abuse_spam_filtering_en" class="input textarea" rows="2"></textarea>
      </div>
      <div class="field">
        <label>{{ t.config.abuseRfc2142 }} (DE)</label>
        <textarea v-model="settings.abuse_rfc2142" class="input textarea" rows="2"></textarea>
      </div>
      <div class="field">
        <label>{{ t.config.abuseRfc2142 }} (EN)</label>
        <textarea v-model="settings.abuse_rfc2142_en" class="input textarea" rows="2"></textarea>
      </div>
    </div>

    <div class="actions">
      <button class="btn btn-primary" :disabled="saving" @click="save">
        <i class="pi pi-save"></i> {{ saving ? t.common.loading : t.config.save }}
      </button>
      <button class="btn btn-secondary" @click="openPreview">
        <i class="pi pi-external-link"></i> {{ t.config.abusePagePreview }}
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

.textarea {
  resize: vertical;
  min-height: 3rem;
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

.btn-secondary:hover {
  background: #e2e8f0;
}
</style>
