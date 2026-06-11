<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useToast } from 'primevue/usetoast'
import api from '../api/client'
import { useApi } from '../composables/useApi'
import t from '../i18n/de'

const toast = useToast()
const { call, silent } = useApi()

const loading = ref(false)
const saving = ref(false)
const scanning = ref(false)
const sendingTest = ref(false)

// Editable settings
const enabled = ref(false)
const intervalHours = ref(6)
const lookbackHours = ref(24)
const alertOnChangeOnly = ref(true)
const mailTo = ref('')
const mailFrom = ref('')

// Server info (for delisting prefill — our hostname/PTR)
const serverName = ref('')
const serverIp = ref('')

// Blocks
interface Delisting { portal: string; docs: string; steps: string[]; variant: string; variant_label: string; note: string }
interface Block {
  id: number
  provider: string
  provider_label: string
  blocked_ip: string
  relay_host: string | null
  block_code: string | null
  sample_response: string | null
  sample_queue_id: string | null
  first_seen: string | null
  last_seen: string | null
  hit_count: number
  status: string
  delisting_submitted_at: string | null
  resolved_at: string | null
  delisting: Delisting | null
}
const blocks = ref<Block[]>([])
const lastScanTime = ref('')
const expandedId = ref<number | null>(null)

interface ProviderBlockSettings {
  provider_block_enabled?: string
  provider_block_scan_interval_hours?: string
  provider_block_lookback_hours?: string
  provider_block_alert_on_change_only?: string
  provider_block_mail_to?: string
  provider_block_mail_from?: string
  provider_block_last_scan_time?: string
}

interface ServerInfo {
  name?: string
  ip?: string
}

function loadSettings(data: ProviderBlockSettings) {
  enabled.value = data.provider_block_enabled === 'true'
  intervalHours.value = parseInt(data.provider_block_scan_interval_hours || '6')
  lookbackHours.value = parseInt(data.provider_block_lookback_hours || '24')
  alertOnChangeOnly.value = data.provider_block_alert_on_change_only !== 'false'
  mailTo.value = data.provider_block_mail_to || ''
  mailFrom.value = data.provider_block_mail_from || ''
  lastScanTime.value = data.provider_block_last_scan_time || ''
}

async function fetchServerInfo() {
  const data = await silent(() => api.get<ServerInfo>('/rbl/server-info'))
  if (data !== null) {
    serverName.value = data.name || ''
    serverIp.value = data.ip || ''
  }
}

async function fetchSettings() {
  loading.value = true
  const data = await silent(() => api.get<ProviderBlockSettings>('/provider-blocks'))
  if (data !== null) loadSettings(data)
  loading.value = false
}

async function fetchBlocks() {
  const data = await silent(() => api.get<Block[]>('/provider-blocks/blocks'))
  if (data !== null) blocks.value = data
}

async function saveSettings() {
  saving.value = true
  const payload = {
    provider_block_enabled: enabled.value ? 'true' : 'false',
    provider_block_scan_interval_hours: String(intervalHours.value),
    provider_block_lookback_hours: String(lookbackHours.value),
    provider_block_alert_on_change_only: alertOnChangeOnly.value ? 'true' : 'false',
    provider_block_mail_to: mailTo.value,
    provider_block_mail_from: mailFrom.value,
  }
  const data = await call(
    () => api.put<ProviderBlockSettings>('/provider-blocks', payload),
    { success: t.providerBlocks.settingsSaved },
  )
  if (data !== null) loadSettings(data)
  saving.value = false
}

async function runScan() {
  scanning.value = true
  const data = await call(
    () => api.post<{ scan_time?: string }>('/provider-blocks/scan'),
    { success: t.providerBlocks.scanComplete },
  )
  if (data !== null) {
    lastScanTime.value = data.scan_time || ''
    await fetchBlocks()
  }
  scanning.value = false
}

async function sendTestEmail() {
  sendingTest.value = true
  const data = await silent(() => api.post<{ success: boolean }>('/provider-blocks/test-email'))
  if (data?.success) {
    toast.add({ severity: 'success', summary: t.common.success, detail: t.providerBlocks.testEmailSent, life: 3000 })
  } else {
    toast.add({ severity: 'error', summary: t.common.error, detail: t.providerBlocks.testEmailFailed, life: 5000 })
  }
  sendingTest.value = false
}

async function markSubmitted(b: Block) {
  const data = await call(
    () => api.post<Block>(`/provider-blocks/blocks/${b.id}/submitted`),
    { success: t.providerBlocks.markSubmittedDone },
  )
  if (data !== null) Object.assign(b, data)
}

async function markResolved(b: Block) {
  if (!confirm(t.providerBlocks.confirmResolve)) return
  const result = await call(
    () => api.post<void>(`/provider-blocks/blocks/${b.id}/resolve`),
    { success: t.providerBlocks.markResolvedDone },
  )
  if (result !== null) await fetchBlocks()
}

function toggleExpand(id: number) {
  expandedId.value = expandedId.value === id ? null : id
}

function copyInfo(b: Block) {
  const text = [
    `Gesperrte IP: ${b.blocked_ip}`,
    `Hostname (PTR): ${serverName.value || '—'}`,
    `Provider: ${b.provider_label}`,
    b.delisting?.variant_label ? `Sperr-Typ: ${b.delisting.variant_label}` : '',
    b.block_code ? `Code: ${b.block_code}` : '',
    b.sample_response ? `Bounce: ${b.sample_response}` : '',
  ].filter(Boolean).join('\n')
  navigator.clipboard?.writeText(text).then(() => {
    toast.add({ severity: 'success', summary: t.common.success, detail: t.providerBlocks.copied, life: 2000 })
  })
}

function fmt(ts: string | null): string {
  if (!ts) return '—'
  try { return new Date(ts).toLocaleString('de-DE') } catch { return ts }
}

function statusLabel(s: string): string {
  if (s === 'resolved') return t.providerBlocks.statusResolved
  if (s === 'acknowledged') return t.providerBlocks.statusAcknowledged
  return t.providerBlocks.statusActive
}

const activeCount = computed(() => blocks.value.filter(b => b.status === 'active').length)
const formattedScanTime = computed(() => fmt(lastScanTime.value))

onMounted(() => {
  fetchServerInfo()
  fetchSettings()
  fetchBlocks()
})
</script>

<template>
  <div class="provider-blocks">
    <h2>{{ t.providerBlocks.title }}</h2>
    <p class="page-subtitle">{{ t.providerBlocks.subtitle }}</p>

    <!-- Settings Card -->
    <div class="card">
      <h3>{{ t.providerBlocks.settings }}</h3>

      <div class="form-grid">
        <div class="form-row">
          <label>{{ t.providerBlocks.enabled }}</label>
          <label class="switch">
            <input type="checkbox" v-model="enabled">
            <span class="slider"></span>
          </label>
          <span class="hint">{{ t.providerBlocks.enabledHint }}</span>
        </div>

        <div class="form-row">
          <label>{{ t.providerBlocks.interval }}</label>
          <input type="number" v-model="intervalHours" min="1" max="168" class="input-sm">
          <span class="hint">{{ t.providerBlocks.intervalUnit }}</span>
        </div>

        <div class="form-row">
          <label>{{ t.providerBlocks.lookback }}</label>
          <input type="number" v-model="lookbackHours" min="1" max="720" class="input-sm">
          <span class="hint">{{ t.providerBlocks.lookbackUnit }}</span>
        </div>

        <div class="form-row">
          <label>{{ t.providerBlocks.alertOnChangeOnly }}</label>
          <label class="switch">
            <input type="checkbox" v-model="alertOnChangeOnly">
            <span class="slider"></span>
          </label>
          <span class="hint">{{ t.providerBlocks.alertOnChangeOnlyHint }}</span>
        </div>
      </div>

      <h4>{{ t.providerBlocks.emailSettings }}</h4>
      <div class="form-grid">
        <div class="form-row">
          <label>{{ t.providerBlocks.mailTo }}</label>
          <input type="email" v-model="mailTo" :placeholder="t.providerBlocks.mailToPlaceholder" class="input-md">
          <button class="btn btn-sm btn-secondary" @click="sendTestEmail" :disabled="sendingTest || !mailTo || !mailFrom">
            <i :class="sendingTest ? 'pi pi-spin pi-spinner' : 'pi pi-envelope'"></i>
            {{ sendingTest ? t.providerBlocks.testEmailSending : t.providerBlocks.testEmail }}
          </button>
        </div>
        <div class="form-row">
          <label>{{ t.providerBlocks.mailFrom }}</label>
          <input type="email" v-model="mailFrom" :placeholder="t.providerBlocks.mailFromPlaceholder" class="input-md">
        </div>
      </div>

      <div class="button-bar">
        <button class="btn btn-primary" @click="saveSettings" :disabled="saving">
          <i class="pi pi-save"></i> {{ saving ? t.common.loading : t.common.save }}
        </button>
      </div>
    </div>

    <!-- Results Card -->
    <div class="card">
      <div class="results-header">
        <h3>{{ t.providerBlocks.results }}</h3>
        <div class="results-actions">
          <span v-if="lastScanTime" class="last-check">{{ t.providerBlocks.lastScan }}: {{ formattedScanTime }}</span>
          <button class="btn btn-primary" @click="runScan" :disabled="scanning">
            <i :class="scanning ? 'pi pi-spin pi-spinner' : 'pi pi-refresh'"></i>
            {{ scanning ? t.providerBlocks.scanning : t.providerBlocks.scanNow }}
          </button>
        </div>
      </div>

      <div v-if="blocks.length === 0" class="empty-state">
        <i class="pi pi-check-circle" style="font-size: 2rem; color: #22c55e"></i>
        <p>{{ t.providerBlocks.noBlocks }}</p>
      </div>

      <div v-else>
        <div class="summary-bar" :class="activeCount > 0 ? 'summary-warning' : 'summary-ok'">
          <i :class="activeCount > 0 ? 'pi pi-exclamation-triangle' : 'pi pi-check-circle'"></i>
          <span v-if="activeCount > 0">{{ activeCount }} {{ t.providerBlocks.activeFound }}</span>
          <span v-else>{{ t.providerBlocks.allClear }}</span>
        </div>

        <div v-for="b in blocks" :key="b.id" class="block-item" :class="{ resolved: b.status !== 'active' }">
          <div class="block-head" @click="toggleExpand(b.id)">
            <i class="pi block-chevron" :class="expandedId === b.id ? 'pi-chevron-down' : 'pi-chevron-right'"></i>
            <span class="block-provider">{{ b.provider_label }}</span>
            <code class="block-ip">{{ b.blocked_ip }}</code>
            <span v-if="b.block_code" class="badge badge-code">{{ b.block_code }}</span>
            <span class="block-spacer"></span>
            <span class="block-meta">{{ t.providerBlocks.lastSeen }}: {{ fmt(b.last_seen) }} · {{ b.hit_count }} {{ t.providerBlocks.hits }}</span>
            <span class="badge" :class="b.status === 'active' ? 'badge-danger' : 'badge-success'">{{ statusLabel(b.status) }}</span>
          </div>

          <div v-if="expandedId === b.id" class="block-detail">
            <div class="detail-grid">
              <div><span class="dl">{{ t.providerBlocks.provider }}:</span> {{ b.provider_label }}</div>
              <div><span class="dl">{{ t.providerBlocks.blockedIp }}:</span> <code>{{ b.blocked_ip }}</code></div>
              <div v-if="b.relay_host"><span class="dl">{{ t.providerBlocks.relayHost }}:</span> <code>{{ b.relay_host }}</code></div>
              <div><span class="dl">{{ t.providerBlocks.firstSeen }}:</span> {{ fmt(b.first_seen) }}</div>
              <div><span class="dl">{{ t.providerBlocks.lastSeen }}:</span> {{ fmt(b.last_seen) }}</div>
              <div v-if="b.delisting_submitted_at"><span class="dl">{{ t.providerBlocks.submittedAt }}:</span> {{ fmt(b.delisting_submitted_at) }}</div>
            </div>

            <div v-if="b.sample_response" class="sample-box">
              <span class="dl">{{ t.providerBlocks.sampleBounce }}:</span>
              <pre>{{ b.sample_response }}</pre>
            </div>

            <h4>{{ t.providerBlocks.delistingGuide }}</h4>
            <div v-if="b.delisting?.variant_label" class="variant-line">
              <span class="dl">{{ t.providerBlocks.blockType }}:</span> {{ b.delisting.variant_label }}
            </div>
            <div v-if="b.delisting?.note" class="note-box">
              <i class="pi pi-exclamation-triangle"></i>
              <span>{{ b.delisting.note }}</span>
            </div>
            <ol class="steps">
              <li v-for="(step, i) in (b.delisting?.steps || [])" :key="i">{{ step }}</li>
            </ol>

            <div class="detail-actions">
              <a v-if="b.delisting?.portal" :href="b.delisting.portal" target="_blank" rel="noopener" class="btn btn-sm btn-primary">
                <i class="pi pi-external-link"></i> {{ t.providerBlocks.delistingPortal }}
              </a>
              <a v-if="b.delisting?.docs" :href="b.delisting.docs" target="_blank" rel="noopener" class="btn btn-sm btn-secondary">
                <i class="pi pi-book"></i> {{ t.providerBlocks.docs }}
              </a>
              <button class="btn btn-sm btn-secondary" @click="copyInfo(b)">
                <i class="pi pi-copy"></i> {{ t.providerBlocks.copyInfo }}
              </button>
              <span class="detail-spacer"></span>
              <button v-if="b.status === 'active'" class="btn btn-sm btn-secondary" @click="markSubmitted(b)" :disabled="!!b.delisting_submitted_at">
                <i class="pi pi-send"></i> {{ b.delisting_submitted_at ? t.providerBlocks.markSubmittedDone : t.providerBlocks.markSubmitted }}
              </button>
              <button v-if="b.status === 'active'" class="btn btn-sm btn-success" @click="markResolved(b)">
                <i class="pi pi-check"></i> {{ t.providerBlocks.markResolved }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.provider-blocks { padding: 1.5rem; }
.provider-blocks h2 { margin: 0 0 0.25rem 0; font-size: 1.5rem; font-weight: 600; }
.page-subtitle { margin: 0 0 1.5rem 0; color: #64748b; font-size: 0.9rem; max-width: 70ch; }

.card {
  background: white;
  border-radius: 12px;
  padding: 1.5rem;
  margin-bottom: 1.5rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}
.card h3 { margin: 0 0 1rem 0; font-size: 1.1rem; font-weight: 600; }
.card h4 { margin: 1.25rem 0 0.75rem 0; font-size: 0.95rem; font-weight: 600; color: #475569; }

.form-grid { display: flex; flex-direction: column; gap: 0.75rem; }
.form-row { display: flex; align-items: center; gap: 0.75rem; }
.form-row > label:first-child { width: 200px; flex-shrink: 0; font-size: 0.9rem; font-weight: 500; color: #334155; }
.hint { font-size: 0.8rem; color: #94a3b8; }

input[type="text"], input[type="email"], input[type="number"] {
  padding: 0.5rem 0.75rem; border: 1px solid #d1d5db; border-radius: 6px;
  font-size: 0.9rem; outline: none; transition: border-color 0.15s;
}
input:focus { border-color: #3b82f6; }
.input-sm { width: 90px; }
.input-md { width: 280px; }

/* Toggle switch */
.switch { position: relative; display: inline-block; width: 44px; height: 24px; flex-shrink: 0; }
.switch input { opacity: 0; width: 0; height: 0; }
.slider { position: absolute; cursor: pointer; inset: 0; background-color: #cbd5e1; transition: 0.2s; border-radius: 24px; }
.slider::before { content: ""; position: absolute; height: 18px; width: 18px; left: 3px; bottom: 3px; background-color: white; transition: 0.2s; border-radius: 50%; }
.switch input:checked + .slider { background-color: #3b82f6; }
.switch input:checked + .slider::before { transform: translateX(20px); }

code { background: #f1f5f9; padding: 0.15rem 0.4rem; border-radius: 4px; font-size: 0.85rem; }

/* Buttons */
.btn { display: inline-flex; align-items: center; gap: 0.4rem; padding: 0.5rem 1rem; border: none; border-radius: 6px; font-size: 0.9rem; cursor: pointer; transition: all 0.15s; text-decoration: none; }
.btn:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-primary { background: #3b82f6; color: white; }
.btn-primary:hover:not(:disabled) { background: #2563eb; }
.btn-secondary { background: #64748b; color: white; }
.btn-secondary:hover:not(:disabled) { background: #475569; }
.btn-success { background: #22c55e; color: white; }
.btn-success:hover:not(:disabled) { background: #16a34a; }
.btn-sm { padding: 0.35rem 0.65rem; font-size: 0.8rem; }
.button-bar { margin-top: 1.5rem; display: flex; gap: 0.5rem; }

/* Results header */
.results-header { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 0.75rem; margin-bottom: 1rem; }
.results-header h3 { margin: 0; }
.results-actions { display: flex; align-items: center; gap: 1rem; }
.last-check { font-size: 0.85rem; color: #64748b; }

.empty-state { text-align: center; padding: 3rem 1rem; color: #94a3b8; }
.empty-state p { margin: 0.75rem 0 0; }

.summary-bar { display: flex; align-items: center; gap: 0.5rem; padding: 0.75rem 1rem; border-radius: 8px; font-weight: 500; margin-bottom: 1rem; }
.summary-ok { background: #f0fdf4; color: #166534; }
.summary-warning { background: #fef2f2; color: #991b1b; }

.badge { display: inline-block; padding: 0.15rem 0.5rem; border-radius: 4px; font-size: 0.75rem; font-weight: 600; }
.badge-success { background: #dcfce7; color: #166534; }
.badge-danger { background: #fee2e2; color: #991b1b; }
.badge-code { background: #fef9c3; color: #854d0e; }

/* Block items */
.block-item { border: 1px solid #e2e8f0; border-radius: 8px; margin-bottom: 0.6rem; overflow: hidden; }
.block-item.resolved { opacity: 0.7; }
.block-head { display: flex; align-items: center; gap: 0.6rem; padding: 0.7rem 0.9rem; cursor: pointer; }
.block-head:hover { background: #f8fafc; }
.block-chevron { color: #94a3b8; font-size: 0.8rem; }
.block-provider { font-weight: 600; color: #1e293b; }
.block-ip { font-weight: 600; }
.block-spacer { flex: 1; }
.block-meta { font-size: 0.78rem; color: #94a3b8; }

.block-detail { padding: 0.9rem; border-top: 1px solid #f1f5f9; background: #fbfcfe; }
.detail-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 0.4rem 1.5rem; font-size: 0.88rem; margin-bottom: 0.75rem; }
.dl { font-weight: 600; color: #475569; }

.sample-box { margin-bottom: 0.75rem; }
.sample-box pre { background: #f1f5f9; border-radius: 6px; padding: 0.6rem 0.8rem; font-size: 0.8rem; white-space: pre-wrap; word-break: break-word; margin: 0.3rem 0 0; }

.variant-line { font-size: 0.88rem; margin-bottom: 0.5rem; }
.note-box { display: flex; gap: 0.5rem; align-items: flex-start; background: #fffbeb; border: 1px solid #fde68a; color: #92400e; border-radius: 6px; padding: 0.6rem 0.8rem; font-size: 0.85rem; margin-bottom: 0.75rem; }
.note-box .pi { margin-top: 0.1rem; }

.steps { margin: 0 0 1rem; padding-left: 1.2rem; font-size: 0.88rem; color: #334155; }
.steps li { margin-bottom: 0.35rem; }

.detail-actions { display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap; }
.detail-spacer { flex: 1; }
</style>
