<script setup lang="ts">
import { ref, computed } from 'vue'
import InputText from 'primevue/inputtext'
import Password from 'primevue/password'
import Checkbox from 'primevue/checkbox'
import Button from 'primevue/button'
import t from '../../i18n/de'

const props = defineProps<{
  user: { id: number; username: string; is_admin: boolean } | null
}>()

const emit = defineEmits<{
  save: [data: { username?: string; password?: string; is_admin?: boolean }, userId?: number]
  cancel: []
}>()

const isEditing = computed(() => !!props.user)

const username = ref(props.user?.username ?? '')
const password = ref('')
const isAdmin = ref(props.user?.is_admin ?? false)

function save() {
  if (isEditing.value && props.user) {
    emit('save', { password: password.value || undefined, is_admin: isAdmin.value }, props.user.id)
  } else {
    emit('save', { username: username.value, password: password.value, is_admin: isAdmin.value })
  }
}
</script>

<template>
  <div class="card">
    <h3>{{ isEditing ? t.users.edit : t.users.addUser }}</h3>
    <form @submit.prevent="save" class="user-form">
      <div v-if="!isEditing" class="field">
        <label>{{ t.users.username }}</label>
        <InputText v-model="username" :placeholder="t.users.username" class="w-full" />
      </div>
      <div class="field">
        <label>{{ t.users.password }}{{ isEditing ? ' (leer lassen um nicht zu aendern)' : '' }}</label>
        <Password
          v-model="password"
          :placeholder="t.users.password"
          :feedback="false"
          toggle-mask
          class="w-full"
          input-class="w-full"
        />
      </div>
      <div class="checkbox-field">
        <Checkbox v-model="isAdmin" :binary="true" input-id="is-admin" />
        <label for="is-admin">{{ t.users.admin }}</label>
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

.user-form {
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

.w-full {
  width: 100%;
}

.checkbox-field {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.checkbox-field label {
  font-size: 0.9rem;
  color: #334155;
}

.actions {
  display: flex;
  gap: 0.75rem;
}
</style>
