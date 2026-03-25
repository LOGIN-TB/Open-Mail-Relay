<script setup lang="ts">
import { ref } from 'vue'
import InputText from 'primevue/inputtext'
import Button from 'primevue/button'
import t from '../../i18n/de'

const emit = defineEmits<{
  save: [payload: { name: string; category: string; monthly_limit: number; description: string }]
  cancel: []
}>()

const name = ref('')
const category = ref('transaction')
const monthlyLimit = ref(1000)
const description = ref('')

const categories = [
  { value: 'transaction', label: t.billing.transaction },
  { value: 'newsletter', label: t.billing.newsletter },
  { value: 'overage', label: t.billing.overage },
]

function save() {
  if (name.value.trim() && monthlyLimit.value > 0) {
    emit('save', {
      name: name.value.trim(),
      category: category.value,
      monthly_limit: monthlyLimit.value,
      description: description.value.trim(),
    })
  }
}
</script>

<template>
  <div class="card">
    <h3>{{ t.billing.addPackage }}</h3>
    <form @submit.prevent="save" class="pkg-form">
      <div class="form-row">
        <div class="field">
          <label>{{ t.billing.packageName }}</label>
          <InputText v-model="name" placeholder="z.B. Trans-XL" class="w-full" />
        </div>
        <div class="field">
          <label>{{ t.billing.category }}</label>
          <select v-model="category" class="select-field">
            <option v-for="cat in categories" :key="cat.value" :value="cat.value">
              {{ cat.label }}
            </option>
          </select>
        </div>
        <div class="field">
          <label>{{ t.billing.monthlyLimit }}</label>
          <input v-model.number="monthlyLimit" type="number" min="1" class="input-field w-full" />
          <small class="hint">{{ t.billing.emailsPerMonth }}</small>
        </div>
      </div>
      <div class="field">
        <label>{{ t.billing.description }}</label>
        <InputText v-model="description" class="w-full" />
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

.pkg-form {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.form-row {
  display: flex;
  gap: 1rem;
}

.form-row .field {
  flex: 1;
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

.input-field {
  padding: 0.5rem 0.75rem;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 0.9rem;
  color: #1e293b;
  background: white;
}

.select-field {
  width: 100%;
  padding: 0.5rem 0.75rem;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 0.9rem;
  color: #1e293b;
  background: white;
}

.w-full {
  width: 100%;
}

.actions {
  display: flex;
  gap: 0.75rem;
}
</style>
