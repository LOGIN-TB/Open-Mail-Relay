import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: () => import('../views/LoginView.vue'),
      meta: { public: true },
    },
    {
      path: '/',
      component: () => import('../components/layout/AppLayout.vue'),
      children: [
        {
          path: '',
          name: 'dashboard',
          component: () => import('../views/DashboardView.vue'),
        },
        {
          path: 'protokoll',
          name: 'protokoll',
          component: () => import('../views/ProtokollView.vue'),
        },
        {
          path: 'netzwerke',
          name: 'networks',
          component: () => import('../views/NetzwerkeView.vue'),
        },
        {
          path: 'smtp-benutzer',
          name: 'smtp-users',
          component: () => import('../views/SmtpBenutzerView.vue'),
        },
        {
          path: 'drosselung',
          name: 'throttling',
          component: () => import('../views/DrosselungView.vue'),
        },
        {
          path: 'konfiguration',
          name: 'config',
          component: () => import('../views/KonfigurationView.vue'),
        },
        {
          path: 'benutzer',
          name: 'users',
          component: () => import('../views/BenutzerView.vue'),
        },
      ],
    },
  ],
})

router.beforeEach((to) => {
  const auth = useAuthStore()
  if (!to.meta.public && !auth.isAuthenticated) {
    return { name: 'login' }
  }
})

export default router
