<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import Dialog from 'primevue/dialog'
import InputText from 'primevue/inputtext'
import Checkbox from 'primevue/checkbox'
import Button from 'primevue/button'
import t from '../../i18n/de'

export interface PackageOption {
  id: number
  name: string
}

export interface SmtpUserEditData {
  id: number
  username: string
  company: string | null
  service: string | null
  mail_domain: string | null
  contact_email: string | null
  receive_reports: boolean
  package_id: number | null
}

const props = defineProps<{
  visible: boolean
  user: SmtpUserEditData | null // null = create mode
  packages: PackageOption[]
}>()

const emit = defineEmits<{
  save: [payload: {
    id?: number
    username?: string
    company: string | null
    service: string | null
    mail_domain: string | null
    contact_email: string | null
    receive_reports: boolean
    package_id: number | null
  }]
  close: []
}>()

const username = ref('')
const company = ref('')
const service = ref('')
const mailDomain = ref('')
const contactEmail = ref('')
const packageId = ref(0)
const receiveReports = ref(true)
const emailError = ref('')

const isEdit = computed(() => props.user !== null)
const dialogTitle = computed(() => isEdit.value ? t.smtpUsers.editUser : t.smtpUsers.addUser)
const submitLabel = computed(() => isEdit.value ? t.common.save : t.smtpUsers.addUser)

watch(() => props.visible, (v) => {
  if (v) {
    if (props.user) {
      username.value = props.user.username
      company.value = props.user.company || ''
      service.value = props.user.service || ''
      mailDomain.value = props.user.mail_domain || ''
      contactEmail.value = props.user.contact_email || ''
      receiveReports.value = props.user.receive_reports
      packageId.value = props.user.package_id || 0
    } else {
      username.value = ''
      company.value = ''
      service.value = ''
      mailDomain.value = ''
      contactEmail.value = ''
      receiveReports.value = true
      packageId.value = 0
    }
    emailError.value = ''
  }
})

function validateEmail(val: string): boolean {
  if (!val) return true
  return /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(val)
}

function save() {
  const email = contactEmail.value.trim()
  if (email && !validateEmail(email)) {
    emailError.value = 'Ungueltige E-Mail-Adresse'
    return
  }
  emailError.value = ''

  if (!isEdit.value && !username.value.trim()) return

  const payload: any = {
    company: company.value.trim() || null,
    service: service.value.trim() || null,
    mail_domain: mailDomain.value.trim() || null,
    contact_email: email || null,
    receive_reports: receiveReports.value,
    package_id: packageId.value || null,
  }

  if (isEdit.value) {
    payload.id = props.user!.id
  } else {
    payload.username = username.value.trim().toLowerCase()
  }

  emit('save', payload)
}
</script>

<template>
  <Dialog
    :visible="visible"
    :header="dialogTitle"
    modal
    :closable="true"
    :draggable="false"
    :style="{ width: '520px' }"
    @update:visible="!$event && emit('close')"
  >
    <form @submit.prevent="save" class="dialog-form">
      <!-- Konto -->
      <div class="form-section">
        <div class="section-label">{{ t.smtpUsers.account }}</div>
        <div class="field">
          <label>{{ t.smtpUsers.username }}</label>
          <InputText
            v-model="username"
            :placeholder="t.smtpUsers.usernamePlaceholder"
            :disabled="isEdit"
            class="w-full"
          />
          <small v-if="!isEdit" class="hint">{{ t.smtpUsers.usernameHint }}</small>
        </div>
      </div>

      <!-- Kundendaten -->
      <div class="form-section">
        <div class="section-label">{{ t.smtpUsers.customerData }}</div>
        <div class="field">
          <label>{{ t.smtpUsers.company }}</label>
          <InputText
            v-model="company"
            :placeholder="t.smtpUsers.companyPlaceholder"
            class="w-full"
          />
        </div>
        <div class="field">
          <label>{{ t.smtpUsers.mailDomain }}</label>
          <InputText
            v-model="mailDomain"
            :placeholder="t.smtpUsers.mailDomainPlaceholder"
            class="w-full"
          />
        </div>
        <div class="field">
          <label>{{ t.smtpUsers.contactEmail }}</label>
          <InputText
            v-model="contactEmail"
            :placeholder="t.smtpUsers.contactEmailPlaceholder"
            class="w-full"
            :class="{ 'p-invalid': emailError }"
          />
          <small v-if="emailError" class="error-text">{{ emailError }}</small>
        </div>
      </div>

      <!-- Dienst & Paket -->
      <div class="form-section">
        <div class="section-label">{{ t.smtpUsers.serviceAndPackage }}</div>
        <div class="field">
          <label>{{ t.smtpUsers.service }}</label>
          <InputText
            v-model="service"
            :placeholder="t.smtpUsers.servicePlaceholder"
            class="w-full"
          />
        </div>
        <div class="field">
          <label>{{ t.smtpUsers.package }}</label>
          <select v-model.number="packageId" class="select-field">
            <option :value="0">{{ t.smtpUsers.noPackage }}</option>
            <option v-for="pkg in packages" :key="pkg.id" :value="pkg.id">{{ pkg.name }}</option>
          </select>
        </div>
        <div class="field-checkbox">
          <Checkbox v-model="receiveReports" :binary="true" inputId="receiveReports" />
          <div>
            <label for="receiveReports">{{ t.smtpUsers.receiveReports }}</label>
            <small class="hint">{{ t.smtpUsers.receiveReportsHint }}</small>
          </div>
        </div>
      </div>

      <!-- Actions -->
      <div class="dialog-actions">
        <Button
          :label="t.common.cancel"
          icon="pi pi-times"
          severity="secondary"
          outlined
          @click="emit('close')"
        />
        <Button
          type="submit"
          :label="submitLabel"
          :icon="isEdit ? 'pi pi-check' : 'pi pi-plus'"
        />
      </div>
    </form>
  </Dialog>
</template>

<style scoped>
.dialog-form {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
  padding-top: 0.5rem;
}

.form-section {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.section-label {
  font-size: 0.75rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: #94a3b8;
  padding-bottom: 0.25rem;
  border-bottom: 1px solid #f1f5f9;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
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

.field-checkbox {
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
  padding-top: 0.25rem;
}

.field-checkbox label {
  font-size: 0.85rem;
  font-weight: 600;
  color: #475569;
  cursor: pointer;
}

.field-checkbox .hint {
  display: block;
}

.error-text {
  font-size: 0.75rem;
  color: #dc2626;
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

.dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
  padding-top: 0.5rem;
  border-top: 1px solid #f1f5f9;
}
</style>
