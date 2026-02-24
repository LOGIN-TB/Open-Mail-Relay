<script setup lang="ts">
import { ref } from 'vue'
import { useToast } from 'primevue/usetoast'
import Button from 'primevue/button'
import api from '../../api/client'
import t from '../../i18n/de'

const toast = useToast()

const props = defineProps<{
  user: {
    id: number
    username: string
    password: string
  }
}>()

const emit = defineEmits<{
  close: []
}>()

const copied = ref(false)

function copyPassword() {
  navigator.clipboard.writeText(props.user.password)
  copied.value = true
  toast.add({ severity: 'info', summary: t.smtpUsers.copied, life: 2000 })
  setTimeout(() => { copied.value = false }, 2000)
}

async function downloadPdf() {
  try {
    const response = await api.get(`/smtp-users/${props.user.id}/config-pdf`, {
      responseType: 'blob',
    })
    const url = window.URL.createObjectURL(new Blob([response.data]))
    const link = document.createElement('a')
    link.href = url
    link.download = `smtp-config-${props.user.username}.pdf`
    link.click()
    window.URL.revokeObjectURL(url)
  } catch {
    toast.add({ severity: 'error', summary: t.common.error, detail: 'PDF-Download fehlgeschlagen', life: 5000 })
  }
}
</script>

<template>
  <div class="credentials-overlay" @click.self="emit('close')">
    <div class="credentials-card">
      <div class="card-header">
        <h3>{{ t.smtpUsers.credentialsTitle }}</h3>
        <Button icon="pi pi-times" severity="secondary" size="small" text @click="emit('close')" />
      </div>

      <p class="info-text">{{ t.smtpUsers.credentialsInfo }}</p>

      <div class="credentials-table">
        <div class="cred-row">
          <span class="cred-label">{{ t.smtpUsers.username }}</span>
          <code class="cred-value">{{ user.username }}</code>
        </div>
        <div class="cred-row">
          <span class="cred-label">{{ t.smtpUsers.password }}</span>
          <code class="cred-value password">{{ user.password }}</code>
        </div>
      </div>

      <div class="actions">
        <Button
          :label="copied ? t.smtpUsers.copied : t.smtpUsers.copyPassword"
          :icon="copied ? 'pi pi-check' : 'pi pi-copy'"
          :severity="copied ? 'success' : 'secondary'"
          @click="copyPassword"
        />
        <Button
          :label="t.smtpUsers.downloadPdf"
          icon="pi pi-file-pdf"
          severity="info"
          @click="downloadPdf"
        />
      </div>

      <div class="close-action">
        <Button :label="t.common.confirm" @click="emit('close')" class="w-full" />
      </div>
    </div>
  </div>
</template>

<style scoped>
.credentials-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.credentials-card {
  background: white;
  border-radius: 12px;
  padding: 1.5rem;
  max-width: 480px;
  width: 90%;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.12);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.75rem;
}

.card-header h3 {
  font-size: 1.1rem;
  color: #1e293b;
}

.info-text {
  font-size: 0.85rem;
  color: #64748b;
  margin-bottom: 1rem;
  line-height: 1.5;
}

.credentials-table {
  background: #f8fafc;
  border-radius: 8px;
  padding: 0.75rem;
  margin-bottom: 1rem;
  border: 1px solid #e2e8f0;
}

.cred-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.5rem 0;
}

.cred-row:first-child {
  border-bottom: 1px solid #e2e8f0;
}

.cred-label {
  font-size: 0.85rem;
  color: #64748b;
  font-weight: 500;
}

.cred-value {
  font-size: 0.9rem;
  background: #e2e8f0;
  padding: 2px 8px;
  border-radius: 4px;
  font-weight: 600;
}

.cred-value.password {
  font-size: 1rem;
  background: #fef3c7;
  color: #92400e;
  letter-spacing: 0.5px;
}

.actions {
  display: flex;
  gap: 0.75rem;
  margin-bottom: 1rem;
}

.close-action {
  border-top: 1px solid #e2e8f0;
  padding-top: 1rem;
}

.w-full {
  width: 100%;
}
</style>
