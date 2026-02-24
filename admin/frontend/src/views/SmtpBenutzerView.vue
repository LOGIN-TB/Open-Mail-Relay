<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useToast } from 'primevue/usetoast'
import { useConfirm } from 'primevue/useconfirm'
import api from '../api/client'
import SmtpUserList from '../components/smtp-users/SmtpUserList.vue'
import SmtpUserForm from '../components/smtp-users/SmtpUserForm.vue'
import SmtpUserCredentials from '../components/smtp-users/SmtpUserCredentials.vue'
import t from '../i18n/de'

import type { SmtpUserItem } from '../components/smtp-users/SmtpUserList.vue'

const toast = useToast()
const confirm = useConfirm()

const users = ref<SmtpUserItem[]>([])
const loading = ref(false)
const showForm = ref(false)
const credentialsUser = ref<{ id: number; username: string; password: string } | null>(null)

async function fetchUsers() {
  loading.value = true
  try {
    const { data } = await api.get('/smtp-users')
    users.value = data
  } finally {
    loading.value = false
  }
}

async function createUser(username: string) {
  try {
    const { data } = await api.post('/smtp-users', { username })
    toast.add({ severity: 'success', summary: t.common.success, detail: t.smtpUsers.userCreated, life: 3000 })
    showForm.value = false
    credentialsUser.value = { id: data.id, username: data.username, password: data.password }
    await fetchUsers()
  } catch (e: any) {
    toast.add({ severity: 'error', summary: t.common.error, detail: e.response?.data?.detail ?? 'Fehler', life: 5000 })
  }
}

async function toggleActive(user: SmtpUserItem) {
  try {
    await api.put(`/smtp-users/${user.id}`, { is_active: !user.is_active })
    toast.add({ severity: 'success', summary: t.common.success, detail: t.smtpUsers.userUpdated, life: 3000 })
    await fetchUsers()
  } catch (e: any) {
    toast.add({ severity: 'error', summary: t.common.error, detail: e.response?.data?.detail ?? 'Fehler', life: 5000 })
  }
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
  try {
    const { data } = await api.post(`/smtp-users/${user.id}/regenerate-password`)
    toast.add({ severity: 'success', summary: t.common.success, detail: t.smtpUsers.passwordRegenerated, life: 3000 })
    credentialsUser.value = { id: data.id, username: data.username, password: data.password }
    await fetchUsers()
  } catch (e: any) {
    toast.add({ severity: 'error', summary: t.common.error, detail: e.response?.data?.detail ?? 'Fehler', life: 5000 })
  }
}

async function downloadPdf(user: SmtpUserItem) {
  try {
    const response = await api.get(`/smtp-users/${user.id}/config-pdf`, {
      responseType: 'blob',
    })
    const url = window.URL.createObjectURL(new Blob([response.data]))
    const link = document.createElement('a')
    link.href = url
    link.download = `smtp-config-${user.username}.pdf`
    link.click()
    window.URL.revokeObjectURL(url)
  } catch (e: any) {
    toast.add({ severity: 'error', summary: t.common.error, detail: 'PDF-Download fehlgeschlagen', life: 5000 })
  }
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
  try {
    await api.delete(`/smtp-users/${userId}`)
    toast.add({ severity: 'success', summary: t.common.success, detail: t.smtpUsers.userDeleted, life: 3000 })
    await fetchUsers()
  } catch (e: any) {
    toast.add({ severity: 'error', summary: t.common.error, detail: e.response?.data?.detail ?? 'Fehler', life: 5000 })
  }
}

onMounted(fetchUsers)
</script>

<template>
  <div class="smtp-users-page">
    <div class="page-header">
      <h2>{{ t.smtpUsers.title }}</h2>
      <button class="btn-primary" @click="showForm = true">
        <i class="pi pi-plus"></i> {{ t.smtpUsers.addUser }}
      </button>
    </div>

    <SmtpUserForm
      v-if="showForm"
      @save="createUser"
      @cancel="showForm = false"
    />

    <SmtpUserList
      :users="users"
      :loading="loading"
      @toggle-active="toggleActive"
      @regenerate-password="confirmRegenerate"
      @download-pdf="downloadPdf"
      @delete="confirmDelete"
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
