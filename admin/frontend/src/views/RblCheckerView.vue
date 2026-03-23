<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useToast } from 'primevue/usetoast'
import api from '../api/client'
import t from '../i18n/de'

const toast = useToast()

const settings = ref<any>({})
const loading = ref(false)
const saving = ref(false)
const checking = ref(false)
const sendingTest = ref(false)

// Server info (auto-detected from Postfix config)
const serverName = ref('')
const serverIp = ref('')

// Editable fields
const enabled = ref(false)
const intervalHours = ref(6)
const mailTo = ref('')
const mailFrom = ref('')
const alertOnChangeOnly = ref(false)
const dnsTimeout = ref(5)

// Additional server list
const servers = ref<{ name: string; ip: string }[]>([])
const newServerName = ref('')
const newServerIp = ref('')

// Results
const lastResults = ref<any>(null)
const lastCheckTime = ref('')

function loadSettingsIntoForm(data: any) {
  enabled.value = data.rbl_enabled === 'true'
  intervalHours.value = parseInt(data.rbl_check_interval_hours || '6')
  mailTo.value = data.rbl_mail_to || ''
  mailFrom.value = data.rbl_mail_from || ''
  alertOnChangeOnly.value = data.rbl_alert_on_change_only === 'true'
  dnsTimeout.value = parseInt(data.rbl_dns_timeout || '5')

  try {
    servers.value = JSON.parse(data.rbl_servers || '[]')
  } catch {
    servers.value = []
  }

  try {
    const results = JSON.parse(data.rbl_last_results || '{}')
    lastResults.value = results.results && results.results.length > 0 ? results : null
  } catch {
    lastResults.value = null
  }

  lastCheckTime.value = data.rbl_last_check_time || ''
}

async function fetchServerInfo() {
  try {
    const { data } = await api.get('/rbl/server-info')
    serverName.value = data.name || ''
    serverIp.value = data.ip || ''
  } catch {
    // ignore
  }
}

async function fetchSettings() {
  loading.value = true
  try {
    const { data } = await api.get('/rbl')
    settings.value = data
    loadSettingsIntoForm(data)
  } finally {
    loading.value = false
  }
}

async function saveSettings() {
  saving.value = true
  try {
    const payload: any = {
      rbl_enabled: enabled.value ? 'true' : 'false',
      rbl_check_interval_hours: String(intervalHours.value),
      rbl_mail_to: mailTo.value,
      rbl_mail_from: mailFrom.value,
      rbl_alert_on_change_only: alertOnChangeOnly.value ? 'true' : 'false',
      rbl_dns_timeout: String(dnsTimeout.value),
      rbl_servers: JSON.stringify(servers.value),
    }
    const { data } = await api.put('/rbl', payload)
    settings.value = data
    loadSettingsIntoForm(data)
    toast.add({ severity: 'success', summary: t.common.success, detail: t.rbl.settingsSaved, life: 3000 })
  } catch (e: any) {
    toast.add({ severity: 'error', summary: t.common.error, detail: e.response?.data?.detail ?? 'Fehler', life: 5000 })
  } finally {
    saving.value = false
  }
}

async function runCheck() {
  checking.value = true
  try {
    const { data } = await api.post('/rbl/check')
    lastResults.value = data.results && data.results.length > 0 ? data : null
    lastCheckTime.value = data.check_time || ''
    toast.add({ severity: 'success', summary: t.common.success, detail: t.rbl.checkComplete, life: 3000 })
  } catch (e: any) {
    toast.add({ severity: 'error', summary: t.common.error, detail: e.response?.data?.detail ?? 'Fehler', life: 5000 })
  } finally {
    checking.value = false
  }
}

async function sendTestEmail() {
  sendingTest.value = true
  try {
    const { data } = await api.post('/rbl/test-email')
    if (data.success) {
      toast.add({ severity: 'success', summary: t.common.success, detail: t.rbl.testEmailSent, life: 3000 })
    } else {
      toast.add({ severity: 'error', summary: t.common.error, detail: t.rbl.testEmailFailed, life: 5000 })
    }
  } catch (e: any) {
    toast.add({ severity: 'error', summary: t.common.error, detail: t.rbl.testEmailFailed, life: 5000 })
  } finally {
    sendingTest.value = false
  }
}

function addServer() {
  const name = newServerName.value.trim()
  const ip = newServerIp.value.trim()
  if (!name || !ip) return
  if (!/^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$/.test(ip)) {
    toast.add({ severity: 'error', summary: t.common.error, detail: t.rbl.invalidIp, life: 3000 })
    return
  }
  servers.value.push({ name, ip })
  newServerName.value = ''
  newServerIp.value = ''
}

function removeServer(index: number) {
  servers.value.splice(index, 1)
}

const formattedCheckTime = computed(() => {
  if (!lastCheckTime.value) return ''
  try {
    return new Date(lastCheckTime.value).toLocaleString('de-DE')
  } catch {
    return lastCheckTime.value
  }
})

const totalListings = computed(() => {
  if (!lastResults.value?.results) return 0
  return lastResults.value.results.reduce((sum: number, r: any) => sum + (r.listed_count || 0), 0)
})

onMounted(() => {
  fetchServerInfo()
  fetchSettings()
})
</script>

<template>
  <div class="rbl-checker">
    <h2>{{ t.rbl.title }}</h2>

    <!-- Settings Card -->
    <div class="card">
      <h3>{{ t.rbl.settings }}</h3>

      <div class="form-grid">
        <div class="form-row">
          <label>{{ t.rbl.enabled }}</label>
          <label class="switch">
            <input type="checkbox" v-model="enabled">
            <span class="slider"></span>
          </label>
          <span class="hint">{{ t.rbl.enabledHint }}</span>
        </div>

        <div class="form-row">
          <label>{{ t.rbl.interval }}</label>
          <input type="number" v-model="intervalHours" min="1" max="168" class="input-sm">
          <span class="hint">{{ t.rbl.intervalUnit }}</span>
        </div>

        <div class="form-row">
          <label>{{ t.rbl.dnsTimeout }}</label>
          <input type="number" v-model="dnsTimeout" min="1" max="30" class="input-sm">
          <span class="hint">{{ t.rbl.dnsTimeoutUnit }}</span>
        </div>

        <div class="form-row">
          <label>{{ t.rbl.alertOnChangeOnly }}</label>
          <label class="switch">
            <input type="checkbox" v-model="alertOnChangeOnly">
            <span class="slider"></span>
          </label>
          <span class="hint">{{ t.rbl.alertOnChangeOnlyHint }}</span>
        </div>
      </div>

      <h4>{{ t.rbl.emailSettings }}</h4>
      <div class="form-grid">
        <div class="form-row">
          <label>{{ t.rbl.mailTo }}</label>
          <input type="email" v-model="mailTo" :placeholder="t.rbl.mailToPlaceholder" class="input-md">
          <button
            class="btn btn-sm btn-secondary"
            @click="sendTestEmail"
            :disabled="sendingTest || !mailTo || !mailFrom"
          >
            <i :class="sendingTest ? 'pi pi-spin pi-spinner' : 'pi pi-envelope'"></i>
            {{ sendingTest ? t.rbl.testEmailSending : t.rbl.testEmail }}
          </button>
        </div>
        <div class="form-row">
          <label>{{ t.rbl.mailFrom }}</label>
          <input type="email" v-model="mailFrom" :placeholder="t.rbl.mailFromPlaceholder" class="input-md">
        </div>
      </div>

      <h4>{{ t.rbl.ownServer }}</h4>
      <p class="hint">{{ t.rbl.ownServerHint }}</p>
      <div class="server-info-box" v-if="serverName || serverIp">
        <div class="server-info-item">
          <span class="server-info-label">Hostname:</span>
          <code>{{ serverName }}</code>
        </div>
        <div class="server-info-item">
          <span class="server-info-label">IP:</span>
          <code>{{ serverIp || '—' }}</code>
        </div>
      </div>

      <h4>{{ t.rbl.additionalServers }}</h4>

      <table v-if="servers.length" class="data-table server-table">
        <thead>
          <tr>
            <th>{{ t.rbl.serverName }}</th>
            <th>{{ t.rbl.serverIp }}</th>
            <th>{{ t.rbl.actions }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(srv, idx) in servers" :key="idx">
            <td>{{ srv.name }}</td>
            <td><code>{{ srv.ip }}</code></td>
            <td>
              <button class="btn btn-sm btn-danger" @click="removeServer(idx)">
                <i class="pi pi-trash"></i>
              </button>
            </td>
          </tr>
        </tbody>
      </table>

      <div class="add-server-row">
        <input
          type="text"
          v-model="newServerName"
          :placeholder="t.rbl.serverNamePlaceholder"
          class="input-md"
          @keyup.enter="addServer"
        >
        <input
          type="text"
          v-model="newServerIp"
          :placeholder="t.rbl.serverIpPlaceholder"
          class="input-md"
          @keyup.enter="addServer"
        >
        <button class="btn btn-sm btn-primary" @click="addServer" :disabled="!newServerName.trim() || !newServerIp.trim()">
          <i class="pi pi-plus"></i> {{ t.rbl.addServer }}
        </button>
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
        <h3>{{ t.rbl.results }}</h3>
        <div class="results-actions">
          <span v-if="lastCheckTime" class="last-check">
            {{ t.rbl.lastCheck }}: {{ formattedCheckTime }}
          </span>
          <button class="btn btn-primary" @click="runCheck" :disabled="checking || !serverIp">
            <i :class="checking ? 'pi pi-spin pi-spinner' : 'pi pi-refresh'"></i>
            {{ checking ? t.rbl.checking : t.rbl.checkNow }}
          </button>
        </div>
      </div>

      <div v-if="!lastResults" class="empty-state">
        <i class="pi pi-shield" style="font-size: 2rem; color: #94a3b8"></i>
        <p>{{ t.rbl.noResults }}</p>
      </div>

      <div v-else>
        <div class="summary-bar" :class="totalListings > 0 ? 'summary-warning' : 'summary-ok'">
          <i :class="totalListings > 0 ? 'pi pi-exclamation-triangle' : 'pi pi-check-circle'"></i>
          <span v-if="totalListings > 0">
            {{ totalListings }} {{ t.rbl.listingsFound }}
          </span>
          <span v-else>{{ t.rbl.allClean }}</span>
        </div>

        <table class="data-table results-table">
          <thead>
            <tr>
              <th>{{ t.rbl.serverName }}</th>
              <th>IP</th>
              <th>{{ t.rbl.checked }}</th>
              <th>{{ t.rbl.listed }}</th>
              <th>{{ t.rbl.status }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="r in lastResults.results" :key="r.ip">
              <td>{{ r.name }}</td>
              <td><code>{{ r.ip }}</code></td>
              <td>{{ r.checked }}</td>
              <td>{{ r.listed_count }}</td>
              <td>
                <span v-if="r.listed_count === 0" class="badge badge-success">CLEAN</span>
                <span v-else class="badge badge-danger">{{ r.listed_count }} LISTINGS</span>
              </td>
            </tr>
          </tbody>
        </table>

        <!-- Listing details -->
        <template v-for="r in lastResults.results" :key="'detail-' + r.ip">
          <div v-if="r.listings && r.listings.length > 0" class="listing-details">
            <h4>{{ r.name }} ({{ r.ip }}) — {{ t.rbl.listings }}</h4>
            <table class="data-table">
              <thead>
                <tr>
                  <th>{{ t.rbl.rblName }}</th>
                  <th>Zone</th>
                  <th>{{ t.rbl.answer }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="listing in r.listings" :key="listing.rbl_zone">
                  <td>{{ listing.rbl_name }}</td>
                  <td><code>{{ listing.rbl_zone }}</code></td>
                  <td><code>{{ listing.answer }}</code></td>
                </tr>
              </tbody>
            </table>
          </div>
        </template>
      </div>
    </div>
  </div>
</template>

<style scoped>
.rbl-checker {
  padding: 1.5rem;
}

.rbl-checker h2 {
  margin: 0 0 1.5rem 0;
  font-size: 1.5rem;
  font-weight: 600;
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
  width: 200px;
  flex-shrink: 0;
  font-size: 0.9rem;
  font-weight: 500;
  color: #334155;
}

.hint {
  font-size: 0.8rem;
  color: #94a3b8;
}

input[type="text"],
input[type="email"],
input[type="number"],
input[type="password"] {
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

.input-sm {
  width: 80px;
}

.input-md {
  width: 280px;
}

/* Toggle switch */
.switch {
  position: relative;
  display: inline-block;
  width: 44px;
  height: 24px;
  flex-shrink: 0;
}

.switch input {
  opacity: 0;
  width: 0;
  height: 0;
}

.slider {
  position: absolute;
  cursor: pointer;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: #cbd5e1;
  transition: 0.2s;
  border-radius: 24px;
}

.slider::before {
  content: "";
  position: absolute;
  height: 18px;
  width: 18px;
  left: 3px;
  bottom: 3px;
  background-color: white;
  transition: 0.2s;
  border-radius: 50%;
}

.switch input:checked + .slider {
  background-color: #3b82f6;
}

.switch input:checked + .slider::before {
  transform: translateX(20px);
}

/* Server info box */
.server-info-box {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 0.75rem 1rem;
  display: flex;
  gap: 2rem;
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

/* Tables */
.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.9rem;
  margin-top: 0.5rem;
}

.data-table th {
  text-align: left;
  padding: 0.6rem 0.75rem;
  border-bottom: 2px solid #e2e8f0;
  font-weight: 600;
  color: #475569;
  font-size: 0.8rem;
  text-transform: uppercase;
  letter-spacing: 0.02em;
}

.data-table td {
  padding: 0.6rem 0.75rem;
  border-bottom: 1px solid #f1f5f9;
}

.data-table tbody tr:hover {
  background: #f8fafc;
}

.server-table {
  margin-bottom: 1rem;
}

code {
  background: #f1f5f9;
  padding: 0.15rem 0.4rem;
  border-radius: 4px;
  font-size: 0.85rem;
}

/* Add server row */
.add-server-row {
  display: flex;
  gap: 0.5rem;
  align-items: center;
  margin-top: 0.5rem;
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

.btn-danger {
  background: #ef4444;
  color: white;
}

.btn-danger:hover:not(:disabled) {
  background: #dc2626;
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

.results-actions {
  display: flex;
  align-items: center;
  gap: 1rem;
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

.badge-danger {
  background: #fee2e2;
  color: #991b1b;
}

.listing-details {
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 1px solid #e2e8f0;
}

.listing-details h4 {
  margin: 0 0 0.5rem 0;
  color: #991b1b;
}
</style>
