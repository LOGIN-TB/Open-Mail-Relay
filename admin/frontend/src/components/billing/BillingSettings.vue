<script setup lang="ts">
import { ref, watch } from 'vue'
import InputText from 'primevue/inputtext'
import Checkbox from 'primevue/checkbox'
import Button from 'primevue/button'
import t from '../../i18n/de'

const props = defineProps<{
  reportEmail: string
  reportFrom: string
  usageReportEnabled: boolean
  usageReportDay: string
}>()

const emit = defineEmits<{
  save: [payload: {
    billing_report_email: string
    billing_report_from: string
    usage_report_enabled: boolean
    usage_report_day: string
  }]
}>()

const email = ref(props.reportEmail)
const from = ref(props.reportFrom)
const usageEnabled = ref(props.usageReportEnabled)
const usageDay = ref(props.usageReportDay)

watch(() => props.reportEmail, (v) => { email.value = v })
watch(() => props.reportFrom, (v) => { from.value = v })
watch(() => props.usageReportEnabled, (v) => { usageEnabled.value = v })
watch(() => props.usageReportDay, (v) => { usageDay.value = v })

const dayOptions = [
  { value: 'monday', label: t.billing.monday },
  { value: 'tuesday', label: t.billing.tuesday },
  { value: 'wednesday', label: t.billing.wednesday },
  { value: 'thursday', label: t.billing.thursday },
  { value: 'friday', label: t.billing.friday },
  { value: 'saturday', label: t.billing.saturday },
  { value: 'sunday', label: t.billing.sunday },
]

function save() {
  emit('save', {
    billing_report_email: email.value.trim(),
    billing_report_from: from.value.trim(),
    usage_report_enabled: usageEnabled.value,
    usage_report_day: usageDay.value,
  })
}
</script>

<template>
  <form @submit.prevent="save">
    <div class="settings-grid">

      <!-- Linker Block: Monatsbericht -->
      <div class="card">
        <h3>Monatsbericht (intern)</h3>
        <p class="description">Monatliche Gesamtauswertung aller SMTP-Benutzer mit Paket-, Kontingent- und Zusatzpaket-Uebersicht. Wird am 1. des Monats automatisch an den Administrator gesendet.</p>
        <div class="fields">
          <div class="field">
            <label>{{ t.billing.reportEmail }}</label>
            <InputText v-model="email" :placeholder="t.billing.reportEmailPlaceholder" class="w-full" />
          </div>
          <div class="field">
            <label>{{ t.billing.reportFrom }}</label>
            <InputText v-model="from" :placeholder="t.billing.reportFromPlaceholder" class="w-full" />
          </div>
        </div>
      </div>

      <!-- Rechter Block: Kontingent-Berichte -->
      <div class="card">
        <h3>{{ t.billing.usageReports }} (Kunden)</h3>
        <p class="description">{{ t.billing.usageReportEnabledHint }}. Jeder Kunde erhaelt eine individuelle Uebersicht mit Paket, Limit und aktuellem Verbrauch fuer den laufenden Monat.</p>
        <div class="fields">
          <div class="field-checkbox">
            <Checkbox v-model="usageEnabled" :binary="true" inputId="usageEnabled" />
            <label for="usageEnabled">{{ t.billing.usageReportEnabled }}</label>
          </div>
          <div class="field">
            <label>{{ t.billing.usageReportDay }}</label>
            <select v-model="usageDay" class="select-field" :disabled="!usageEnabled">
              <option v-for="opt in dayOptions" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
            </select>
          </div>
        </div>
      </div>

    </div>

    <!-- Save -->
    <div class="form-actions">
      <Button type="submit" :label="t.common.save" icon="pi pi-check" />
    </div>
  </form>
</template>

<style scoped>
.settings-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}

.card {
  background: white;
  border-radius: 12px;
  padding: 1.25rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
  border: 1px solid #e2e8f0;
  display: flex;
  flex-direction: column;
}

.card h3 {
  font-size: 1rem;
  color: #1e293b;
  margin: 0 0 0.5rem 0;
}

.description {
  font-size: 0.8rem;
  color: #64748b;
  line-height: 1.5;
  margin: 0 0 1rem 0;
}

.fields {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
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

.field-checkbox {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.field-checkbox label {
  font-size: 0.85rem;
  font-weight: 600;
  color: #475569;
  cursor: pointer;
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

.select-field:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 1rem;
}

.w-full {
  width: 100%;
}
</style>
