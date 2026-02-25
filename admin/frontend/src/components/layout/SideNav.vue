<script setup lang="ts">
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '../../stores/auth'
import { useLayoutStore } from '../../stores/layout'
import t from '../../i18n/de'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const layout = useLayoutStore()

const navItems = [
  { label: t.nav.dashboard, icon: 'pi pi-chart-bar', to: '/' },
  { label: t.nav.protokoll, icon: 'pi pi-list', to: '/protokoll' },
  { label: t.nav.networks, icon: 'pi pi-globe', to: '/netzwerke' },
  { label: t.nav.smtpUsers, icon: 'pi pi-key', to: '/smtp-benutzer' },
  { label: t.nav.throttling, icon: 'pi pi-gauge', to: '/drosselung' },
  { label: t.nav.config, icon: 'pi pi-cog', to: '/konfiguration' },
  { label: t.nav.users, icon: 'pi pi-users', to: '/benutzer' },
]

function isActive(path: string) {
  if (path === '/') return route.path === '/'
  return route.path.startsWith(path)
}

const appVersion = __APP_VERSION__

function logout() {
  auth.logout()
  router.push({ name: 'login' })
}
</script>

<template>
  <nav class="sidebar" :class="{ collapsed: layout.collapsed }">
    <div class="logo">
      <i class="pi pi-envelope" style="font-size: 1.5rem"></i>
      <span v-show="!layout.collapsed" class="logo-text">Open Mail Relay</span>
    </div>

    <ul class="nav-list">
      <li v-for="item in navItems" :key="item.to">
        <router-link
          :to="item.to"
          class="nav-item"
          :class="{ active: isActive(item.to) }"
          :title="layout.collapsed ? item.label : undefined"
        >
          <i :class="item.icon"></i>
          <span v-show="!layout.collapsed">{{ item.label }}</span>
        </router-link>
      </li>
    </ul>

    <div class="sidebar-footer">
      <button
        class="nav-item toggle-btn"
        @click="layout.toggleSidebar()"
        :title="layout.collapsed ? 'Seitenleiste ausklappen' : 'Seitenleiste einklappen'"
      >
        <i :class="layout.collapsed ? 'pi pi-angle-double-right' : 'pi pi-angle-double-left'"></i>
        <span v-show="!layout.collapsed">Einklappen</span>
      </button>
      <button class="nav-item logout-btn" @click="logout" :title="layout.collapsed ? t.nav.logout : undefined">
        <i class="pi pi-sign-out"></i>
        <span v-show="!layout.collapsed">{{ t.nav.logout }}</span>
      </button>
      <div v-show="!layout.collapsed" class="version">v{{ appVersion }}</div>
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
  transition: width 0.2s ease;
  overflow: hidden;
}

.logo {
  padding: 0 1.25rem;
  height: 56px;
  display: flex;
  align-items: center;
  gap: 0.75rem;
  font-size: 1.2rem;
  font-weight: 700;
  border-bottom: 1px solid #334155;
  white-space: nowrap;
}

.sidebar.collapsed .logo {
  justify-content: center;
  padding: 0;
}

.nav-list {
  list-style: none;
  padding: 0.5rem;
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
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
  white-space: nowrap;
}

.sidebar.collapsed .nav-item {
  justify-content: center;
  padding: 0.75rem;
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

.toggle-btn {
  color: #64748b;
}

.toggle-btn:hover {
  background: #334155;
  color: #e2e8f0;
}

.logout-btn {
  color: #f87171;
}

.logout-btn:hover {
  background: #451a1a;
  color: #fca5a5;
}

.version {
  text-align: center;
  font-size: 0.75rem;
  color: #475569;
  padding: 0.25rem 0;
}
</style>
