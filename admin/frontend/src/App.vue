<script setup lang="ts">
import { watch } from 'vue'
import { RouterView } from 'vue-router'
import Toast from 'primevue/toast'
import ConfirmDialog from 'primevue/confirmdialog'
import { useLayoutStore } from './stores/layout'

const layout = useLayoutStore()

function applySidebarWidth() {
  document.documentElement.style.setProperty('--sidebar-width', layout.sidebarWidth)
}

applySidebarWidth()
watch(() => layout.sidebarWidth, applySidebarWidth)
</script>

<template>
  <Toast position="top-right" />
  <ConfirmDialog />
  <RouterView />
</template>

<style>
:root {
  --sidebar-width: 260px;
}

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  background: #f8fafc;
  color: #1e293b;
}

a {
  text-decoration: none;
  color: inherit;
}
</style>
