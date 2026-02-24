<script setup lang="ts">
import { useAuthStore } from '../../stores/auth'

const auth = useAuthStore()
</script>

<template>
  <header class="topbar">
    <div class="topbar-content">
      <div class="spacer"></div>
      <div class="user-info">
        <i class="pi pi-user"></i>
        <span>{{ auth.user?.username ?? '...' }}</span>
        <span v-if="auth.isAdmin" class="badge">Admin</span>
      </div>
    </div>
  </header>
</template>

<style scoped>
.topbar {
  background: white;
  border-bottom: 1px solid #e2e8f0;
  padding: 0 1.5rem;
  height: 56px;
  display: flex;
  align-items: center;
}

.topbar-content {
  display: flex;
  align-items: center;
  width: 100%;
}

.spacer {
  flex: 1;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: #475569;
  font-size: 0.9rem;
}

.badge {
  background: #3b82f6;
  color: white;
  font-size: 0.7rem;
  padding: 2px 8px;
  border-radius: 12px;
  font-weight: 600;
}
</style>
