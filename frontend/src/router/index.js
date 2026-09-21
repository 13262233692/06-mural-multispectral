import { createRouter, createWebHistory } from 'vue-router'

import { useAuthStore } from '@/stores/auth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', name: 'login', component: () => import('@/views/LoginView.vue') },
    { path: '/projects', name: 'projects', component: () => import('@/views/ProjectListView.vue') },
    {
      path: '/projects/:projectId',
      name: 'workbench',
      component: () => import('@/views/WorkbenchView.vue'),
    },
    { path: '/', redirect: '/projects' },
  ],
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  if (to.name !== 'login' && !auth.isLoggedIn) return { name: 'login' }
  if (auth.isLoggedIn && !auth.user) {
    try {
      await auth.fetchMe()
    } catch {
      auth.logout()
      return { name: 'login' }
    }
  }
  if (to.name === 'login' && auth.isLoggedIn) return { name: 'projects' }
  return true
})

export default router
