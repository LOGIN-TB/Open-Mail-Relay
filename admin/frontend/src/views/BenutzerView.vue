<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useToast } from 'primevue/usetoast'
import { useConfirm } from 'primevue/useconfirm'
import api from '../api/client'
import UserList from '../components/users/UserList.vue'
import UserForm from '../components/users/UserForm.vue'
import t from '../i18n/de'

const toast = useToast()
const confirm = useConfirm()

const users = ref<any[]>([])
const loading = ref(false)
const showForm = ref(false)
const editingUser = ref<any>(null)

async function fetchUsers() {
  loading.value = true
  try {
    const { data } = await api.get('/auth/users')
    users.value = data
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editingUser.value = null
  showForm.value = true
}

function openEdit(user: any) {
  editingUser.value = user
  showForm.value = true
}

async function saveUser(data: { username?: string; password?: string; is_admin?: boolean }, userId?: number) {
  try {
    if (userId) {
      await api.put(`/auth/users/${userId}`, { password: data.password || undefined, is_admin: data.is_admin })
    } else {
      await api.post('/auth/users', data)
    }
    toast.add({ severity: 'success', summary: t.common.success, detail: 'Benutzer gespeichert', life: 3000 })
    showForm.value = false
    await fetchUsers()
  } catch (e: any) {
    toast.add({ severity: 'error', summary: t.common.error, detail: e.response?.data?.detail ?? 'Fehler', life: 5000 })
  }
}

function confirmDelete(user: any) {
  confirm.require({
    message: t.users.confirmDelete,
    header: t.users.delete,
    icon: 'pi pi-exclamation-triangle',
    acceptClass: 'p-button-danger',
    accept: () => deleteUser(user.id),
  })
}

async function deleteUser(userId: number) {
  try {
    await api.delete(`/auth/users/${userId}`)
    toast.add({ severity: 'success', summary: t.common.success, detail: 'Benutzer geloescht', life: 3000 })
    await fetchUsers()
  } catch (e: any) {
    toast.add({ severity: 'error', summary: t.common.error, detail: e.response?.data?.detail ?? 'Fehler', life: 5000 })
  }
}

onMounted(fetchUsers)
</script>

<template>
  <div class="users-page">
    <div class="page-header">
      <h2>{{ t.users.title }}</h2>
      <button class="btn-primary" @click="openCreate">
        <i class="pi pi-plus"></i> {{ t.users.addUser }}
      </button>
    </div>

    <UserForm
      v-if="showForm"
      :user="editingUser"
      @save="saveUser"
      @cancel="showForm = false"
    />

    <UserList
      :users="users"
      :loading="loading"
      @edit="openEdit"
      @delete="confirmDelete"
    />
  </div>
</template>

<style scoped>
.users-page {
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
