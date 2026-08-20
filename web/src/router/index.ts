import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  { path: '/', redirect: '/home' },
  {
    path: '/login',
    name: 'login',
    component: () => import('../views/Login.vue'),
    meta: { requiresAuth: false },
  },
  {
    path: '/register',
    name: 'register',
    component: () => import('../views/Register.vue'),
    meta: { requiresAuth: false },
  },
  {
    path: '/home',
    name: 'home',
    component: () => import('../views/Home.vue'),
    meta: { requiresAuth: true, tabbar: true, title: '首页' },
  },
  {
    path: '/aid-order',
    name: 'aid-order',
    component: () => import('../views/AidOrder.vue'),
    meta: { requiresAuth: true, title: '援助下单' },
  },
  {
    path: '/reservation',
    name: 'reservation',
    component: () => import('../views/Reservation.vue'),
    meta: { requiresAuth: true, title: '预约' },
  },
  {
    path: '/credit',
    name: 'credit',
    component: () => import('../views/Credit.vue'),
    meta: { requiresAuth: true, title: '信用等级' },
  },
  {
    path: '/orders',
    name: 'orders',
    component: () => import('../views/Orders.vue'),
    meta: { requiresAuth: true, tabbar: true, title: '订单' },
  },
  {
    path: '/orders/:id',
    name: 'order-detail',
    component: () => import('../views/OrderDetail.vue'),
    meta: { requiresAuth: true, title: '订单详情' },
  },
  {
    path: '/orders/:id/match',
    name: 'order-match',
    component: () => import('../views/OrderMatch.vue'),
    meta: { requiresAuth: true, title: '订单撮合' },
  },
  {
    path: '/team',
    name: 'team',
    component: () => import('../views/Team.vue'),
    meta: { requiresAuth: true, tabbar: true, title: '我的团队' },
  },
  {
    path: '/account',
    name: 'account',
    component: () => import('../views/Account.vue'),
    meta: { requiresAuth: true, tabbar: true, title: '我的账户' },
  },
  {
    path: '/account/transactions',
    name: 'transactions',
    component: () => import('../views/Transactions.vue'),
    meta: { requiresAuth: true, title: '交易流水' },
  },
  {
    path: '/withdraw',
    name: 'withdraw',
    component: () => import('../views/Withdraw.vue'),
    meta: { requiresAuth: true, title: '提现' },
  },
  {
    path: '/notifications',
    name: 'notifications',
    component: () => import('../views/Notifications.vue'),
    meta: { requiresAuth: true, title: '通知中心' },
  },
  {
    path: '/announcements',
    name: 'announcements',
    component: () => import('../views/Announcements.vue'),
    meta: { requiresAuth: true, title: '平台公告' },
  },
  {
    path: '/profile',
    name: 'profile',
    component: () => import('../views/Profile.vue'),
    meta: { requiresAuth: true, tabbar: true, title: '我的' },
  },
  {
    path: '/security',
    name: 'security',
    component: () => import('../views/Security.vue'),
    meta: { requiresAuth: true, title: '安全设置' },
  },
  {
    path: '/customer-service',
    name: 'customer-service',
    component: () => import('../views/CustomerService.vue'),
    meta: { requiresAuth: true, title: '客服中心' },
  },
  {
    path: '/appeal',
    name: 'appeal',
    component: () => import('../views/Appeal.vue'),
    meta: { requiresAuth: true, title: '申诉' },
  },
  { path: '/:pathMatch(.*)*', redirect: '/home' },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to) => {
  const token = localStorage.getItem('lx_token')
  if (to.meta.requiresAuth && !token) {
    return { path: '/login', query: { redirect: to.fullPath } }
  }
  return true
})

export default router