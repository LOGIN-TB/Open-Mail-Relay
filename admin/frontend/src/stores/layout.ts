import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useLayoutStore = defineStore('layout', () => {
  const collapsed = ref(localStorage.getItem('sidebar-collapsed') === 'true')

  const sidebarWidth = computed(() => (collapsed.value ? '72px' : '260px'))

  function toggleSidebar() {
    collapsed.value = !collapsed.value
    localStorage.setItem('sidebar-collapsed', String(collapsed.value))
  }

  return { collapsed, sidebarWidth, toggleSidebar }
})
