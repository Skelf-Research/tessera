import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'dashboard',
    component: () => import('../views/Dashboard.vue')
  },
  {
    path: '/customers',
    name: 'customers',
    component: () => import('../views/Customers.vue'),
    meta: { requiresOrg: true }
  },
  {
    path: '/commitments',
    name: 'commitments',
    component: () => import('../views/Commitments.vue')
  },
  {
    path: '/proofs',
    name: 'proofs',
    component: () => import('../views/Proofs.vue')
  },
  {
    path: '/settings',
    name: 'settings',
    component: () => import('../views/Settings.vue')
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
