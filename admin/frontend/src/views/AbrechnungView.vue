<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useToast } from 'primevue/usetoast'
import { useConfirm } from 'primevue/useconfirm'
import api from '../api/client'
import PackageList from '../components/billing/PackageList.vue'
import PackageForm from '../components/billing/PackageForm.vue'
import BillingOverview from '../components/billing/BillingOverview.vue'
import BillingSettingsComp from '../components/billing/BillingSettings.vue'
import t from '../i18n/de'

import type { PackageItem } from '../components/billing/PackageList.vue'
import type { BillingData } from '../components/billing/BillingOverview.vue'

const toast = useToast()
const confirm = useConfirm()

const packages = ref<PackageItem[]>([])
const billingData = ref<BillingData | null>(null)
const loadingPkgs = ref(false)
const loadingBilling = ref(false)
const showPackageForm = ref(false)
const sendingReport = ref(false)

const reportEmail = ref('')
const reportFrom = ref('')
const usageReportEnabled = ref(true)
const usageReportDay = ref('monday')

// Month selector
const now = new Date()
const selectedMonth = ref(`${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`)

function getMonthOptions(): { value: string; label: string }[] {
  const opts = []
  const d = new Date()
  for (let i = 0; i < 12; i++) {
    const ym = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
    const label = d.toLocaleDateString('de-DE', { year: 'numeric', month: 'long' })
    opts.push({ value: ym, label })
    d.setMonth(d.getMonth() - 1)
  }
  return opts
}
const monthOptions = getMonthOptions()

// --- Packages ---

async function fetchPackages() {
  loadingPkgs.value = true
  try {
    const { data } = await api.get('/billing/packages')
    packages.value = data
  } finally {
    loadingPkgs.value = false
  }
}

async function createPackage(payload: { name: string; category: string; monthly_limit: number; description: string }) {
  try {
    await api.post('/billing/packages', payload)
    toast.add({ severity: 'success', summary: t.common.success, detail: t.billing.packageCreated, life: 3000 })
    showPackageForm.value = false
    await fetchPackages()
  } catch (e: any) {
    toast.add({ severity: 'error', summary: t.common.error, detail: e.response?.data?.detail ?? 'Fehler', life: 5000 })
  }
}

async function updatePackageField(packageId: number, field: string, value: string | number) {
  try {
    await api.put(`/billing/packages/${packageId}`, { [field]: value })
    toast.add({ severity: 'success', summary: t.common.success, detail: t.billing.packageUpdated, life: 3000 })
    await fetchPackages()
  } catch (e: any) {
    toast.add({ severity: 'error', summary: t.common.error, detail: e.response?.data?.detail ?? 'Fehler', life: 5000 })
  }
}

function confirmDeletePackage(pkg: PackageItem) {
  confirm.require({
    message: t.billing.confirmDelete,
    header: t.billing.deletePackage,
    icon: 'pi pi-exclamation-triangle',
    acceptClass: 'p-button-danger',
    accept: () => deletePackage(pkg.id),
  })
}

async function deletePackage(packageId: number) {
  try {
    await api.delete(`/billing/packages/${packageId}`)
    toast.add({ severity: 'success', summary: t.common.success, detail: t.billing.packageDeleted, life: 3000 })
    await fetchPackages()
  } catch (e: any) {
    toast.add({ severity: 'error', summary: t.common.error, detail: e.response?.data?.detail ?? 'Fehler', life: 5000 })
  }
}

// --- Billing Overview ---

async function fetchBilling() {
  loadingBilling.value = true
  try {
    const { data } = await api.get(`/billing/overview?year_month=${selectedMonth.value}`)
    billingData.value = data
  } finally {
    loadingBilling.value = false
  }
}

async function refreshBilling() {
  loadingBilling.value = true
  try {
    await api.post(`/billing/overview/refresh?year_month=${selectedMonth.value}`)
    await fetchBilling()
  } catch (e: any) {
    toast.add({ severity: 'error', summary: t.common.error, detail: e.response?.data?.detail ?? 'Fehler', life: 5000 })
    loadingBilling.value = false
  }
}

async function sendReport() {
  sendingReport.value = true
  try {
    await api.post(`/billing/report/${selectedMonth.value}/send`)
    toast.add({ severity: 'success', summary: t.common.success, detail: t.billing.reportSent, life: 3000 })
  } catch (e: any) {
    toast.add({ severity: 'error', summary: t.common.error, detail: e.response?.data?.detail ?? t.billing.reportFailed, life: 5000 })
  } finally {
    sendingReport.value = false
  }
}

// --- Settings ---

async function fetchSettings() {
  try {
    const { data } = await api.get('/billing/settings')
    reportEmail.value = data.billing_report_email || ''
    reportFrom.value = data.billing_report_from || ''
    usageReportEnabled.value = data.usage_report_enabled ?? true
    usageReportDay.value = data.usage_report_day || 'monday'
  } catch { /* ignore */ }
}

async function saveSettings(payload: { billing_report_email: string; billing_report_from: string; usage_report_enabled: boolean; usage_report_day: string }) {
  try {
    await api.put('/billing/settings', payload)
    toast.add({ severity: 'success', summary: t.common.success, detail: t.billing.settingsSaved, life: 3000 })
    await fetchSettings()
  } catch (e: any) {
    toast.add({ severity: 'error', summary: t.common.error, detail: e.response?.data?.detail ?? 'Fehler', life: 5000 })
  }
}

function onMonthChange() {
  fetchBilling()
}

onMounted(() => {
  fetchPackages()
  fetchBilling()
  fetchSettings()
})
</script>

<template>
  <div class="billing-page">
    <!-- Packages Section -->
    <div class="section">
      <div class="page-header">
        <h2>{{ t.billing.packages }}</h2>
        <button class="btn-primary" @click="showPackageForm = true">
          <i class="pi pi-plus"></i> {{ t.billing.addPackage }}
        </button>
      </div>

      <PackageForm
        v-if="showPackageForm"
        @save="createPackage"
        @cancel="showPackageForm = false"
      />

      <PackageList
        :packages="packages"
        :loading="loadingPkgs"
        @delete="confirmDeletePackage"
        @update-field="updatePackageField"
      />
    </div>

    <!-- Billing Overview Section -->
    <div class="section">
      <div class="page-header">
        <h2>{{ t.billing.overview }}</h2>
        <div class="header-actions">
          <select v-model="selectedMonth" class="month-select" @change="onMonthChange">
            <option v-for="opt in monthOptions" :key="opt.value" :value="opt.value">
              {{ opt.label }}
            </option>
          </select>
          <button class="btn-secondary" @click="refreshBilling" :disabled="loadingBilling">
            <i class="pi pi-refresh"></i> {{ t.billing.refresh }}
          </button>
          <button class="btn-primary" @click="sendReport" :disabled="sendingReport">
            <i class="pi pi-send"></i> {{ t.billing.sendReport }}
          </button>
        </div>
      </div>

      <BillingOverview
        :data="billingData"
        :loading="loadingBilling"
      />
    </div>

    <!-- Settings Section -->
    <div class="section">
      <BillingSettingsComp
        :report-email="reportEmail"
        :report-from="reportFrom"
        :usage-report-enabled="usageReportEnabled"
        :usage-report-day="usageReportDay"
        @save="saveSettings"
      />
    </div>
  </div>
</template>

<style scoped>
.billing-page {
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

.section {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.75rem;
}

.page-header h2 {
  font-size: 1.5rem;
  color: #1e293b;
}

.header-actions {
  display: flex;
  gap: 0.5rem;
  align-items: center;
}

.month-select {
  padding: 0.5rem 0.75rem;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  font-size: 0.9rem;
  color: #1e293b;
  background: white;
}

.btn-primary {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.6rem 1.2rem;
  background: #3b82f6;
  color: white;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: 0.9rem;
  font-weight: 500;
  transition: background 0.15s;
}

.btn-primary:hover {
  background: #2563eb;
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-secondary {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.6rem 1.2rem;
  background: #f1f5f9;
  color: #475569;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  cursor: pointer;
  font-size: 0.9rem;
  font-weight: 500;
  transition: background 0.15s;
}

.btn-secondary:hover {
  background: #e2e8f0;
}

.btn-secondary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
</style>
