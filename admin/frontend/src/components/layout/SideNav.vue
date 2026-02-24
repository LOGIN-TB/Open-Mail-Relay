<script setup lang="ts">
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '../../stores/auth'
import t from '../../i18n/de'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()

const navItems = [
  { label: t.nav.dashboard, icon: 'pi pi-chart-bar', to: '/' },
  { label: t.nav.protokoll, icon: 'pi pi-list', to: '/protokoll' },
  { label: t.nav.networks, icon: 'pi pi-globe', to: '/netzwerke' },
  { label: t.nav.config, icon: 'pi pi-cog', to: '/konfiguration' },
  { label: t.nav.users, icon: 'pi pi-users', to: '/benutzer' },
]

function isActive(path: string) {
  if (path === '/') return route.path === '/'
  return route.path.startsWith(path)
}

function logout() {
  auth.logout()
  router.push({ name: 'login' })
}
</script>

<template>
  <nav class="sidebar">
    <div class="logo">
      <i class="pi pi-envelope" style="font-size: 1.5rem"></i>
      <span>Open Mail Relay</span>
    </div>

    <ul class="nav-list">
      <li v-for="item in navItems" :key="item.to">
        <router-link
          :to="item.to"
          class="nav-item"
          :class="{ active: isActive(item.to) }"
        >
          <i :class="item.icon"></i>
          <span>{{ item.label }}</span>
        </router-link>
      </li>
    </ul>

    <div class="sidebar-footer">
      <button class="nav-item logout-btn" @click="logout">
        <i class="pi pi-sign-out"></i>
        <span>{{ t.nav.logout }}</span>
      </button>
    </div>
  </nav>
</template>

<style scoped>
.sidebar {
  position: fixed;
  left: 0;
  top: 0;
  bottom: 0;
  width: var(--sidebar-width);
  background: #1e293b;
  color: #e2e8f0;
  display: flex;
  flex-direction: column;
  z-index: 100;
}

.logo {
  padding: 1.25rem;
  display: flex;
  align-items: center;
  gap: 0.75rem;
  font-size: 1.2rem;
  font-weight: 700;
  border-bottom: 1px solid #334155;
}

.nav-list {
  list-style: none;
  padding: 0.5rem;
  flex: 1;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem 1rem;
  border-radius: 8px;
  color: #94a3b8;
  transition: all 0.15s;
  cursor: pointer;
  border: none;
  background: none;
  width: 100%;
  font-size: 0.95rem;
  text-align: left;
}

.nav-item:hover {
  background: #334155;
  color: #e2e8f0;
}

.nav-item.active {
  background: #3b82f6;
  color: white;
}

.sidebar-footer {
  padding: 0.5rem;
  border-top: 1px solid #334155;
}

.logout-btn {
  color: #f87171;
}

.logout-btn:hover {
  background: #451a1a;
  color: #fca5a5;
}
</style>
