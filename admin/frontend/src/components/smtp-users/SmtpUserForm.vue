<script setup lang="ts">
import { ref } from 'vue'
import InputText from 'primevue/inputtext'
import Button from 'primevue/button'
import t from '../../i18n/de'

const emit = defineEmits<{
  save: [username: string]
  cancel: []
}>()

const username = ref('')

function save() {
  if (username.value.trim()) {
    emit('save', username.value.trim().toLowerCase())
  }
}
</script>

<template>
  <div class="card">
    <h3>{{ t.smtpUsers.addUser }}</h3>
    <form @submit.prevent="save" class="smtp-form">
      <div class="field">
        <label>{{ t.smtpUsers.username }}</label>
        <InputText
          v-model="username"
          :placeholder="t.smtpUsers.usernamePlaceholder"
          class="w-full"
        />
        <small class="hint">{{ t.smtpUsers.usernameHint }}</small>
      </div>
      <div class="actions">
        <Button type="submit" :label="t.common.save" icon="pi pi-check" />
        <Button :label="t.common.cancel" icon="pi pi-times" severity="secondary" @click="emit('cancel')" />
      </div>
    </form>
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
  color: #1e293b;
  margin-bottom: 1rem;
}

.smtp-form {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
}

.field label {
  font-size: 0.85rem;
  font-weight: 600;
  color: #475569;
}

.hint {
  font-size: 0.75rem;
  color: #94a3b8;
}

.w-full {
  width: 100%;
}

.actions {
  display: flex;
  gap: 0.75rem;
}
</style>
