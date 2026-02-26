<script setup lang="ts">
import { ref } from 'vue'
import InputText from 'primevue/inputtext'
import Button from 'primevue/button'
import t from '../../i18n/de'

const cidr = ref('')
const owner = ref('')

const emit = defineEmits<{
  add: [payload: { cidr: string; owner: string }]
}>()

function submit() {
  if (cidr.value.trim()) {
    emit('add', { cidr: cidr.value.trim(), owner: owner.value.trim() })
    cidr.value = ''
    owner.value = ''
  }
}
</script>

<template>
  <div class="card">
    <form @submit.prevent="submit" class="network-form">
      <div class="field">
        <label>{{ t.networks.cidr }}</label>
        <InputText
          v-model="cidr"
          :placeholder="t.networks.cidrPlaceholder"
          class="cidr-input"
        />
      </div>
      <div class="field">
        <label>{{ t.networks.owner }}</label>
        <InputText
          v-model="owner"
          :placeholder="t.networks.ownerPlaceholder"
          class="cidr-input"
        />
      </div>
      <Button
        type="submit"
        :label="t.networks.addNetwork"
        icon="pi pi-plus"
        :disabled="!cidr.trim()"
      />
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

.network-form {
  display: flex;
  align-items: flex-end;
  gap: 1rem;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
  flex: 1;
}

.field label {
  font-size: 0.85rem;
  font-weight: 600;
  color: #475569;
}

.cidr-input {
  width: 100%;
}
</style>
