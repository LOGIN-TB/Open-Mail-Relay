<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useConfirm } from 'primevue/useconfirm'
import api from '../api/client'
import { useApi } from '../composables/useApi'
import SmtpUserList from '../components/smtp-users/SmtpUserList.vue'
import SmtpUserForm from '../components/smtp-users/SmtpUserForm.vue'
import SmtpUserCredentials from '../components/smtp-users/SmtpUserCredentials.vue'
import t from '../i18n/de'

import type { SmtpUser } from '../types/api'
import type { SmtpUserItem } from '../components/smtp-users/SmtpUserList.vue'
import type { SmtpUserEditData } from '../components/smtp-users/SmtpUserForm.vue'

const { call, silent } = useApi()
const confirm = useConfirm()

interface PackageOption {
  id: number
  name: string
}

interface SmtpUserCredentialsData {
  id: number
  username: string
  password: string
}

interface SaveUserPayload {
  id?: number
  username?: string
  company: string | null
  service: string | null
  mail_domain: string | null
  contact_email: string | null
  receive_reports: boolean
  package_id: number | null
}

const users = ref<SmtpUserItem[]>([])
const packages = ref<PackageOption[]>([])
const loading = ref(false)

// Dialog state: null = closed, null user = create, object = edit
const dialogVisible = ref(false)
const dialogUser = ref<SmtpUserEditData | null>(null)

const credentialsUser = ref<SmtpUserCredentialsData | null>(null)

async function fetchPackages() {
  const data = await silent(() => api.get<PackageOption[]>('/billing/packages'))
  if (data !== null) {
    packages.value = data.map((p) => ({ id: p.id, name: p.name }))
  }
}

async function fetchUsers() {
  loading.value = true
  const data = await silent(() => api.get<SmtpUserItem[]>('/smtp-users'))
  if (data !== null) users.value = data
  loading.value = false
}

function openCreate() {
  dialogUser.value = null
  dialogVisible.value = true
}

function openEdit(user: SmtpUserItem) {
  dialogUser.value = {
    id: user.id,
    username: user.username,
    company: user.company,
    service: user.service,
    mail_domain: user.mail_domain,
    contact_email: user.contact_email,
    receive_reports: user.receive_reports,
    package_id: user.package_id,
  }
  dialogVisible.value = true
}

function closeDialog() {
  dialogVisible.value = false
}

async function saveUser(payload: SaveUserPayload) {
  if (payload.id) {
    // Update
    const { id, ...body } = payload
    const result = await call(
      () => api.put<SmtpUser>(`/smtp-users/${id}`, body),
      { success: t.smtpUsers.userUpdated },
    )
    if (result === null) return
    dialogVisible.value = false
  } else {
    // Create
    const data = await call(
      () => api.post<SmtpUserCredentialsData>('/smtp-users', payload),
      { success: t.smtpUsers.userCreated },
    )
    if (data === null) return
    dialogVisible.value = false
    credentialsUser.value = { id: data.id, username: data.username, password: data.password }
  }
  await fetchUsers()
}

async function toggleActive(user: SmtpUserItem) {
  const result = await call(
    () => api.put<SmtpUser>(`/smtp-users/${user.id}`, { is_active: !user.is_active }),
    { success: t.smtpUsers.userUpdated },
  )
  if (result !== null) await fetchUsers()
}

function confirmRegenerate(user: SmtpUserItem) {
  confirm.require({
    message: t.smtpUsers.confirmRegenerate,
    header: t.smtpUsers.regeneratePassword,
    icon: 'pi pi-exclamation-triangle',
    acceptClass: 'p-button-warning',
    accept: () => regeneratePassword(user),
  })
}

async function regeneratePassword(user: SmtpUserItem) {
  const data = await call(
    () => api.post<SmtpUserCredentialsData>(`/smtp-users/${user.id}/regenerate-password`),
    { success: t.smtpUsers.passwordRegenerated },
  )
  if (data === null) return
  credentialsUser.value = { id: data.id, username: data.username, password: data.password }
  await fetchUsers()
}

async function downloadPdf(user: SmtpUserItem) {
  const data = await call(
    () => api.get<Blob>(`/smtp-users/${user.id}/config-pdf`, { responseType: 'blob' }),
    { error: 'PDF-Download fehlgeschlagen' },
  )
  if (data === null) return
  const url = window.URL.createObjectURL(new Blob([data]))
  const link = document.createElement('a')
  link.href = url
  link.download = `smtp-config-${user.username}.pdf`
  link.click()
  window.URL.revokeObjectURL(url)
}

function confirmSendUsageReport(user: SmtpUserItem) {
  confirm.require({
    message: `${t.smtpUsers.confirmSendUsageReport} ${user.contact_email}?`,
    header: t.smtpUsers.sendUsageReport,
    icon: 'pi pi-chart-bar',
    accept: () => sendUsageReport(user),
  })
}

async function sendUsageReport(user: SmtpUserItem) {
  await call(
    () => api.post<void>(`/smtp-users/${user.id}/send-usage-report`),
    { success: t.smtpUsers.usageReportSent },
  )
}

function confirmSendCredentials(user: SmtpUserItem) {
  confirm.require({
    message: `${t.smtpUsers.confirmSendCredentials} ${user.contact_email}?`,
    header: t.smtpUsers.sendCredentials,
    icon: 'pi pi-envelope',
    accept: () => sendCredentials(user),
  })
}

async function sendCredentials(user: SmtpUserItem) {
  await call(
    () => api.post<void>(`/smtp-users/${user.id}/send-credentials`),
    { success: t.smtpUsers.credentialsSent },
  )
}

function confirmDelete(user: SmtpUserItem) {
  confirm.require({
    message: t.smtpUsers.confirmDelete,
    header: t.smtpUsers.delete,
    icon: 'pi pi-exclamation-triangle',
    acceptClass: 'p-button-danger',
    accept: () => deleteUser(user.id),
  })
}

async function deleteUser(userId: number) {
  const result = await call(
    () => api.delete<void>(`/smtp-users/${userId}`),
    { success: t.smtpUsers.userDeleted },
  )
  if (result !== null) await fetchUsers()
}

onMounted(() => {
  fetchUsers()
  fetchPackages()
})
</script>

<template>
  <div class="smtp-users-page">
    <div class="page-header">
      <h2>{{ t.smtpUsers.title }}</h2>
      <button class="btn-primary" @click="openCreate">
        <i class="pi pi-plus"></i> {{ t.smtpUsers.addUser }}
      </button>
    </div>

    <SmtpUserList
      :users="users"
      :packages="packages"
      :loading="loading"
      @edit="openEdit"
      @toggle-active="toggleActive"
      @regenerate-password="confirmRegenerate"
      @download-pdf="downloadPdf"
      @send-credentials="confirmSendCredentials"
      @send-usage-report="confirmSendUsageReport"
      @delete="confirmDelete"
    />

    <SmtpUserForm
      :visible="dialogVisible"
      :user="dialogUser"
      :packages="packages"
      @save="saveUser"
      @close="closeDialog"
    />

    <SmtpUserCredentials
      v-if="credentialsUser"
      :user="credentialsUser"
      @close="credentialsUser = null"
    />
  </div>
</template>

<style scoped>
.smtp-users-page {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.page-header h2 {
  font-size: 1.5rem;
  color: #1e293b;
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
</style>
