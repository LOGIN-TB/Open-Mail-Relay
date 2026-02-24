<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import InputText from 'primevue/inputtext'
import Password from 'primevue/password'
import Button from 'primevue/button'
import t from '../i18n/de'

const router = useRouter()
const auth = useAuthStore()

const username = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)

async function handleLogin() {
  error.value = ''
  loading.value = true
  try {
    await auth.login(username.value, password.value)
    router.push({ name: 'dashboard' })
  } catch (e: any) {
    error.value = e.response?.data?.detail ?? t.login.error
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-page">
    <div class="login-card">
      <div class="login-header">
        <i class="pi pi-envelope" style="font-size: 2rem; color: #3b82f6"></i>
        <h1>{{ t.login.title }}</h1>
        <p>{{ t.login.subtitle }}</p>
      </div>

      <form @submit.prevent="handleLogin" class="login-form">
        <div class="field">
          <label for="username">{{ t.login.username }}</label>
          <InputText
            id="username"
            v-model="username"
            :placeholder="t.login.username"
            class="w-full"
            autofocus
          />
        </div>

        <div class="field">
          <label for="password">{{ t.login.password }}</label>
          <Password
            id="password"
            v-model="password"
            :placeholder="t.login.password"
            :feedback="false"
            toggle-mask
            class="w-full"
            input-class="w-full"
          />
        </div>

        <div v-if="error" class="error-msg">{{ error }}</div>

        <Button
          type="submit"
          :label="t.login.submit"
          :loading="loading"
          class="w-full"
          severity="primary"
        />
      </form>
    </div>
  </div>
</template>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
}

.login-card {
  background: white;
  border-radius: 12px;
  padding: 2.5rem;
  width: 100%;
  max-width: 400px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
}

.login-header {
  text-align: center;
  margin-bottom: 2rem;
}

.login-header h1 {
  font-size: 1.5rem;
  margin-top: 0.75rem;
  color: #1e293b;
}

.login-header p {
  color: #64748b;
  margin-top: 0.25rem;
  font-size: 0.9rem;
}

.login-form {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}

.field label {
  font-size: 0.85rem;
  font-weight: 600;
  color: #475569;
}

.w-full {
  width: 100%;
}

.error-msg {
  color: #ef4444;
  font-size: 0.85rem;
  text-align: center;
  padding: 0.5rem;
  background: #fef2f2;
  border-radius: 6px;
}
</style>
