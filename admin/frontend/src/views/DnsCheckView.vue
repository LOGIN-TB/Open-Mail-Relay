<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useToast } from 'primevue/usetoast'
import api from '../api/client'
import t from '../i18n/de'

const toast = useToast()

const loading = ref(false)
const saving = ref(false)
const checking = ref(false)

// Settings
const dkimSelector = ref('default')

// Server info (auto-detected)
const hostname = ref('')
const serverIp = ref('')
const domain = ref('')

// DKIM key info
const dkimKey = ref<{ exists: boolean; dns_record: string; dns_name: string; selector: string } | null>(null)
const deletingKey = ref(false)
const confirmDelete = ref(false)

// Results
const results = ref<any>(null)
const lastCheckTime = ref('')

async function fetchDkimKey() {
  try {
    const { data } = await api.get('/dns-check/dkim-key')
    dkimKey.value = data
  } catch {
    // ignore
  }
}

async function deleteDkimKey() {
  deletingKey.value = true
  try {
    await api.delete('/dns-check/dkim-key')
    dkimKey.value = null
    confirmDelete.value = false
    toast.add({ severity: 'success', summary: t.common.success, detail: t.dns.dkimKeyDeleted, life: 3000 })
    await fetchDkimKey()
  } catch (e: any) {
    toast.add({ severity: 'error', summary: t.common.error, detail: e.response?.data?.detail ?? 'Fehler', life: 5000 })
  } finally {
    deletingKey.value = false
  }
}

async function fetchSettings() {
  loading.value = true
  try {
    const { data } = await api.get('/dns-check')
    dkimSelector.value = data.dkim_selector || 'default'
    lastCheckTime.value = data.last_check_time || ''
    results.value = data.last_results || null
    if (results.value) {
      hostname.value = results.value.hostname || ''
      serverIp.value = results.value.ip || ''
      domain.value = results.value.domain || ''
    }
  } finally {
    loading.value = false
  }
}

async function saveSettings() {
  saving.value = true
  try {
    const { data } = await api.put('/dns-check', { dkim_selector: dkimSelector.value })
    dkimSelector.value = data.dkim_selector || 'default'
    toast.add({ severity: 'success', summary: t.common.success, detail: t.dns.settingsSaved, life: 3000 })
  } catch (e: any) {
    toast.add({ severity: 'error', summary: t.common.error, detail: e.response?.data?.detail ?? 'Fehler', life: 5000 })
  } finally {
    saving.value = false
  }
}

async function runCheck() {
  checking.value = true
  try {
    const { data } = await api.post('/dns-check/check')
    results.value = data
    lastCheckTime.value = data.check_time || ''
    hostname.value = data.hostname || ''
    serverIp.value = data.ip || ''
    domain.value = data.domain || ''
    toast.add({ severity: 'success', summary: t.common.success, detail: t.dns.checkComplete, life: 3000 })
  } catch (e: any) {
    toast.add({ severity: 'error', summary: t.common.error, detail: e.response?.data?.detail ?? 'Fehler', life: 5000 })
  } finally {
    checking.value = false
  }
}

async function copyToClipboard(text: string) {
  try {
    await navigator.clipboard.writeText(text)
    toast.add({ severity: 'success', summary: t.common.success, detail: t.dns.copied, life: 2000 })
  } catch {
    // fallback
    const el = document.createElement('textarea')
    el.value = text
    document.body.appendChild(el)
    el.select()
    document.execCommand('copy')
    document.body.removeChild(el)
    toast.add({ severity: 'success', summary: t.common.success, detail: t.dns.copied, life: 2000 })
  }
}

const formattedCheckTime = computed(() => {
  if (!lastCheckTime.value) return ''
  try {
    return new Date(lastCheckTime.value).toLocaleString('de-DE')
  } catch {
    return lastCheckTime.value
  }
})

const issueCount = computed(() => {
  if (!results.value) return 0
  let count = 0
  for (const key of ['spf', 'dmarc', 'dkim']) {
    const r = results.value[key]
    if (r && r.status !== 'pass') count++
  }
  return count
})

function statusIcon(status: string): string {
  switch (status) {
    case 'pass': return 'pi pi-check-circle'
    case 'warn': return 'pi pi-exclamation-triangle'
    case 'missing': return 'pi pi-times-circle'
    case 'fail': return 'pi pi-times-circle'
    case 'error': return 'pi pi-exclamation-triangle'
    default: return 'pi pi-question-circle'
  }
}

function statusColor(status: string): string {
  switch (status) {
    case 'pass': return '#166534'
    case 'warn': return '#92400e'
    case 'missing': return '#991b1b'
    case 'fail': return '#991b1b'
    case 'error': return '#92400e'
    default: return '#64748b'
  }
}

function statusLabel(status: string): string {
  switch (status) {
    case 'pass': return t.dns.statusPass
    case 'warn': return t.dns.statusWarn
    case 'fail': return t.dns.statusFail
    case 'missing': return t.dns.statusMissing
    case 'error': return t.dns.statusError
    default: return status
  }
}

function statusBadgeClass(status: string): string {
  switch (status) {
    case 'pass': return 'badge badge-success'
    case 'warn': return 'badge badge-warning'
    default: return 'badge badge-danger'
  }
}

const recordTypes = ['spf', 'dmarc', 'dkim'] as const
function recordTitle(type: string): string {
  return (t.dns as any)[type] || type.toUpperCase()
}
function recordDesc(type: string): string {
  return (t.dns as any)[type + 'Desc'] || ''
}

onMounted(() => {
  fetchSettings()
  fetchDkimKey()
})
</script>

<template>
  <div class="dns-checker">
    <h2>{{ t.dns.title }}</h2>
    <p class="subtitle">{{ t.dns.subtitle }}</p>

    <!-- Settings Card -->
    <div class="card">
      <h3>{{ t.dns.settings }}</h3>

      <div class="form-grid">
        <div class="form-row">
          <label>{{ t.dns.dkimSelector }}</label>
          <input
            type="text"
            v-model="dkimSelector"
            :placeholder="t.dns.dkimSelectorPlaceholder"
            class="input-md"
          >
        </div>
      </div>
      <p class="hint">{{ t.dns.dkimSelectorHint }}</p>

      <!-- Server info -->
      <h4>{{ t.dns.serverInfo }}</h4>
      <div class="server-info-box" v-if="hostname || serverIp || domain">
        <div class="server-info-item">
          <span class="server-info-label">{{ t.dns.hostname }}:</span>
          <code>{{ hostname }}</code>
        </div>
        <div class="server-info-item">
          <span class="server-info-label">{{ t.dns.ip }}:</span>
          <code>{{ serverIp || '—' }}</code>
        </div>
        <div class="server-info-item">
          <span class="server-info-label">{{ t.dns.domain }}:</span>
          <code>{{ domain }}</code>
        </div>
      </div>

      <div class="button-bar">
        <button class="btn btn-secondary" @click="saveSettings" :disabled="saving">
          <i class="pi pi-save"></i> {{ saving ? t.common.loading : t.common.save }}
        </button>
        <button class="btn btn-primary" @click="runCheck" :disabled="checking">
          <i :class="checking ? 'pi pi-spin pi-spinner' : 'pi pi-refresh'"></i>
          {{ checking ? t.dns.checking : t.dns.checkNow }}
        </button>
      </div>
    </div>

    <!-- DKIM Public Key Card -->
    <div class="card" v-if="dkimKey?.exists">
      <div class="dkim-card-header">
        <div>
          <h3>{{ t.dns.dkimPublicKey }}</h3>
          <p class="hint" style="margin-top: 0.25rem">{{ t.dns.dkimPublicKeyHint }}</p>
        </div>
      </div>

      <div class="dkim-key-info">
        <div class="dkim-key-name">
          <span class="meta-label">DNS-Name:</span>
          <code>{{ dkimKey.dns_name }}.{{ domain || '&lt;domain&gt;' }}</code>
        </div>
        <div class="dkim-key-type">
          <span class="meta-label">Typ:</span>
          <code>TXT</code>
        </div>
        <div class="dkim-key-type">
          <span class="meta-label">Selector:</span>
          <code>{{ dkimKey.selector }}</code>
        </div>
      </div>

      <div class="dkim-key-record">
        <code class="suggested-code">{{ dkimKey.dns_record }}</code>
        <button class="btn btn-sm btn-primary" @click="copyToClipboard(dkimKey.dns_record)">
          <i class="pi pi-copy"></i> {{ t.dns.copyRecord }}
        </button>
      </div>

      <div class="dkim-key-actions">
        <template v-if="!confirmDelete">
          <button class="btn btn-sm btn-danger-outline" @click="confirmDelete = true">
            <i class="pi pi-trash"></i> {{ t.dns.dkimKeyDelete }}
          </button>
        </template>
        <template v-else>
          <span class="confirm-text">{{ t.dns.dkimKeyDeleteConfirm }}</span>
          <button class="btn btn-sm btn-danger" @click="deleteDkimKey" :disabled="deletingKey">
            <i :class="deletingKey ? 'pi pi-spin pi-spinner' : 'pi pi-trash'"></i> {{ t.common.confirm }}
          </button>
          <button class="btn btn-sm btn-secondary" @click="confirmDelete = false">
            {{ t.common.cancel }}
          </button>
        </template>
      </div>
    </div>

    <div class="card" v-else-if="dkimKey && !dkimKey.exists">
      <h3>{{ t.dns.dkimPublicKey }}</h3>
      <div class="empty-state" style="padding: 1.5rem">
        <i class="pi pi-key" style="font-size: 1.5rem; color: #94a3b8"></i>
        <p>{{ t.dns.dkimKeyMissing }}</p>
      </div>
    </div>

    <!-- Results Card -->
    <div class="card">
      <div class="results-header">
        <h3>{{ t.dns.results }}</h3>
        <span v-if="lastCheckTime" class="last-check">
          {{ t.dns.lastCheck }}: {{ formattedCheckTime }}
        </span>
      </div>

      <div v-if="!results" class="empty-state">
        <i class="pi pi-globe" style="font-size: 2rem; color: #94a3b8"></i>
        <p>{{ t.dns.noResults }}</p>
      </div>

      <div v-else>
        <!-- Summary bar -->
        <div class="summary-bar" :class="issueCount === 0 ? 'summary-ok' : 'summary-warning'">
          <i :class="issueCount === 0 ? 'pi pi-check-circle' : 'pi pi-exclamation-triangle'"></i>
          <span v-if="issueCount === 0">{{ t.dns.allOk }}</span>
          <span v-else>{{ issueCount }} {{ t.dns.issuesFound }}</span>
        </div>

        <!-- Record sections -->
        <div v-for="type in recordTypes" :key="type" class="record-section">
          <template v-if="results[type]">
            <div class="record-header">
              <i :class="statusIcon(results[type].status)" :style="{ color: statusColor(results[type].status), fontSize: '1.2rem' }"></i>
              <div class="record-title-block">
                <span class="record-title">{{ recordTitle(type) }}</span>
                <span class="record-desc">{{ recordDesc(type) }}</span>
              </div>
              <span :class="statusBadgeClass(results[type].status)">{{ statusLabel(results[type].status) }}</span>
            </div>

            <!-- Lookup domain -->
            <div class="record-meta">
              <span class="meta-label">{{ t.dns.lookupDomain }}:</span>
              <code>{{ results[type].lookup_domain }}</code>
            </div>

            <!-- Found record -->
            <div v-if="results[type].record" class="record-found">
              <span class="meta-label">{{ t.dns.recordFound }}:</span>
              <div class="record-code-box">
                <code class="record-code">{{ results[type].record }}</code>
              </div>
            </div>
            <div v-else-if="results[type].status === 'missing'" class="record-missing">
              <i class="pi pi-info-circle"></i>
              <span>{{ t.dns.recordMissing }}</span>
            </div>

            <!-- Details -->
            <div v-if="results[type].details" class="record-details">
              {{ results[type].details }}
            </div>

            <!-- Suggested record (copy-paste) -->
            <div v-if="results[type].suggested_record" class="suggested-box">
              <div class="suggested-header">
                <i class="pi pi-lightbulb"></i>
                <span class="suggested-title">{{ t.dns.suggestedRecord }}</span>
              </div>
              <p class="suggested-hint">{{ t.dns.suggestedRecordHint }}</p>
              <div class="suggested-record">
                <code class="suggested-code">{{ results[type].suggested_record }}</code>
                <button class="btn btn-sm btn-primary" @click="copyToClipboard(results[type].suggested_record)">
                  <i class="pi pi-copy"></i> {{ t.dns.copyRecord }}
                </button>
              </div>
            </div>
          </template>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.dns-checker {
  padding: 1.5rem;
}

.dns-checker h2 {
  margin: 0 0 0.25rem 0;
  font-size: 1.5rem;
  font-weight: 600;
}

.subtitle {
  margin: 0 0 1.5rem 0;
  color: #64748b;
  font-size: 0.9rem;
}

.card {
  background: white;
  border-radius: 12px;
  padding: 1.5rem;
  margin-bottom: 1.5rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.card h3 {
  margin: 0 0 1rem 0;
  font-size: 1.1rem;
  font-weight: 600;
}

.card h4 {
  margin: 1.5rem 0 0.75rem 0;
  font-size: 0.95rem;
  font-weight: 600;
  color: #475569;
}

.form-grid {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.form-row {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.form-row > label:first-child {
  width: 160px;
  flex-shrink: 0;
  font-size: 0.9rem;
  font-weight: 500;
  color: #334155;
}

.hint {
  font-size: 0.8rem;
  color: #94a3b8;
  margin-top: 0.25rem;
}

input[type="text"] {
  padding: 0.5rem 0.75rem;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 0.9rem;
  outline: none;
  transition: border-color 0.15s;
}

input:focus {
  border-color: #3b82f6;
}

.input-md {
  width: 280px;
}

/* Server info box */
.server-info-box {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 0.75rem 1rem;
  display: flex;
  gap: 2rem;
  flex-wrap: wrap;
}

.server-info-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.9rem;
}

.server-info-label {
  font-weight: 500;
  color: #475569;
}

/* Buttons */
.btn {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.5rem 1rem;
  border: none;
  border-radius: 6px;
  font-size: 0.9rem;
  cursor: pointer;
  transition: all 0.15s;
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
  background: #64748b;
  color: white;
}

.btn-secondary:hover:not(:disabled) {
  background: #475569;
}

.btn-sm {
  padding: 0.35rem 0.65rem;
  font-size: 0.8rem;
}

.button-bar {
  margin-top: 1.5rem;
  display: flex;
  gap: 0.5rem;
}

/* Results */
.results-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.75rem;
  margin-bottom: 1rem;
}

.results-header h3 {
  margin: 0;
}

.last-check {
  font-size: 0.85rem;
  color: #64748b;
}

.empty-state {
  text-align: center;
  padding: 3rem 1rem;
  color: #94a3b8;
}

.empty-state p {
  margin: 0.75rem 0 0;
}

.summary-bar {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1rem;
  border-radius: 8px;
  font-weight: 500;
  margin-bottom: 1rem;
}

.summary-ok {
  background: #f0fdf4;
  color: #166534;
}

.summary-warning {
  background: #fef2f2;
  color: #991b1b;
}

/* Badges */
.badge {
  display: inline-block;
  padding: 0.15rem 0.5rem;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 600;
}

.badge-success {
  background: #dcfce7;
  color: #166534;
}

.badge-warning {
  background: #fef3c7;
  color: #92400e;
}

.badge-danger {
  background: #fee2e2;
  color: #991b1b;
}

code {
  background: #f1f5f9;
  padding: 0.15rem 0.4rem;
  border-radius: 4px;
  font-size: 0.85rem;
}

/* Record sections */
.record-section {
  padding: 1.25rem 0;
  border-top: 1px solid #e2e8f0;
}

.record-section:first-of-type {
  border-top: none;
}

.record-header {
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
  margin-bottom: 0.75rem;
}

.record-title-block {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.record-title {
  font-weight: 600;
  font-size: 0.95rem;
  color: #1e293b;
}

.record-desc {
  font-size: 0.8rem;
  color: #64748b;
  margin-top: 0.15rem;
}

.record-meta {
  font-size: 0.85rem;
  color: #64748b;
  margin-bottom: 0.5rem;
}

.meta-label {
  font-weight: 500;
  color: #475569;
  font-size: 0.85rem;
}

.record-found {
  margin-bottom: 0.5rem;
}

.record-code-box {
  margin-top: 0.35rem;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  padding: 0.5rem 0.75rem;
  overflow-x: auto;
}

.record-code {
  background: none;
  padding: 0;
  font-size: 0.82rem;
  word-break: break-all;
}

.record-missing {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  color: #991b1b;
  font-size: 0.9rem;
  margin-bottom: 0.5rem;
}

.record-details {
  font-size: 0.85rem;
  color: #475569;
  margin-bottom: 0.75rem;
  line-height: 1.5;
}

/* Suggested record box */
.suggested-box {
  background: #fffbeb;
  border: 1px dashed #f59e0b;
  border-radius: 8px;
  padding: 1rem;
  margin-top: 0.5rem;
}

.suggested-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-weight: 600;
  color: #92400e;
  margin-bottom: 0.25rem;
}

.suggested-title {
  font-size: 0.9rem;
}

.suggested-hint {
  font-size: 0.8rem;
  color: #92400e;
  margin: 0 0 0.5rem 0;
}

.suggested-record {
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
}

.suggested-code {
  flex: 1;
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  padding: 0.5rem 0.75rem;
  font-size: 0.82rem;
  word-break: break-all;
  display: block;
}

/* DKIM key card */
.dkim-card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 1rem;
}

.dkim-card-header h3 {
  margin: 0;
}

.dkim-key-info {
  display: flex;
  gap: 2rem;
  margin-bottom: 0.75rem;
  flex-wrap: wrap;
}

.dkim-key-name,
.dkim-key-type {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.9rem;
}

.dkim-key-record {
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
  border-radius: 8px;
  padding: 0.75rem;
}

.dkim-key-actions {
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 1px solid #e2e8f0;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.confirm-text {
  font-size: 0.85rem;
  color: #991b1b;
  font-weight: 500;
}

.btn-danger-outline {
  background: white;
  color: #dc2626;
  border: 1px solid #fca5a5;
}

.btn-danger-outline:hover:not(:disabled) {
  background: #fef2f2;
}

.btn-danger {
  background: #ef4444;
  color: white;
}

.btn-danger:hover:not(:disabled) {
  background: #dc2626;
}
</style>
