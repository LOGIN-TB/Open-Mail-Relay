<script setup lang="ts">
import { RouterView } from 'vue-router'
import SideNav from './SideNav.vue'
import TopBar from './TopBar.vue'
</script>

<template>
  <div class="app-layout">
    <SideNav />
    <div class="main-area">
      <TopBar />
      <main class="content">
        <RouterView />
      </main>
    </div>
  </div>
</template>

<style scoped>
.app-layout {
  display: flex;
  min-height: 100vh;
}

.main-area {
  flex: 1;
  margin-left: var(--sidebar-width);
  display: flex;
  flex-direction: column;
  transition: margin-left 0.2s ease;
}

.content {
  padding: 1.5rem;
  flex: 1;
}

@media (max-width: 768px) {
  .main-area {
    margin-left: 0;
  }
}
</style>
