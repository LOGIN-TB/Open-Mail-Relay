<script setup lang="ts">
import { ref } from 'vue'
import InputText from 'primevue/inputtext'
import Button from 'primevue/button'
import t from '../../i18n/de'

const emit = defineEmits<{
  save: [payload: { ip_address: string; reason: string; notes: string }]
  cancel: []
}>()

const ipAddress = ref('')
const notes = ref('')

function save() {
  if (ipAddress.value.trim()) {
    emit('save', {
      ip_address: ipAddress.value.trim(),
      reason: 'manual',
      notes: notes.value.trim(),
    })
  }
}
</script>

<template>
  <div class="card">
    <h3>{{ t.ipBans.addBan }}</h3>
    <form @submit.prevent="save" class="ban-form">
      <div class="field">
        <label>{{ t.ipBans.ipAddress }}</label>
        <InputText
          v-model="ipAddress"
          :placeholder="t.ipBans.ipPlaceholder"
          class="w-full"
        />
        <small class="hint">{{ t.ipBans.ipHint }}</small>
      </div>
      <div class="field">
        <label>{{ t.ipBans.notes }}</label>
        <InputText
          v-model="notes"
          :placeholder="t.ipBans.notesPlaceholder"
          class="w-full"
        />
      </div>
      <div class="actions">
        <Button type="submit" :label="t.ipBans.ban" icon="pi pi-ban" severity="danger" />
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

.ban-form {
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
