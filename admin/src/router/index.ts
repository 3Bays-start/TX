import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'

declare module 'vue-router' {
  interface RouteMeta {
    title?: string
    public?: boolean
    perm?: string
  }
}

const routes: RouteRecordRaw[] = [
  {
    path: '/admin/login',
    name: 'login',
    component: () => import('@/views/LoginView.vue'),
    meta: { public: true, title: '登录' },
  },
  {
    path: '/admin',
    component: () => import('@/layout/AdminLayout.vue'),
    redirect: '/admin/dashboard',
    children: [
      { path: 'dashboard', name: 'dashboard', component: () => import('@/views/DashboardView.vue'), meta: { title: '数据概览' } },
      { path: 'users', name: 'users', component: () => import('@/views/UsersView.vue'), meta: { title: '用户管理', perm: 'user:view' } },
      { path: 'users/:id', name: 'user-detail', component: () => import('@/views/UserDetailView.vue'), meta: { title: '用户详情', perm: 'user:view' } },
      { path: 'orders', name: 'orders', component: () => import('@/views/OrdersView.vue'), meta: { title: '订单管理', perm: 'order:view' } },
      { path: 'orders/:id', name: 'order-detail', component: () => import('@/views/OrderDetailView.vue'), meta: { title: '订单详情', perm: 'order:view' } },
      { path: 'matching', name: 'matching', component: () => import('@/views/MatchingView.vue'), meta: { title: '撮合管理', perm: 'order:view' } },
      { path: 'accounts', name: 'accounts', component: () => import('@/views/AccountsView.vue'), meta: { title: '账户查询', perm: 'account:view' } },
      { path: 'transactions', name: 'transactions', component: () => import('@/views/TransactionsView.vue'), meta: { title: '交易流水', perm: 'transaction:view' } },
      { path: 'fees', name: 'fees', component: () => import('@/views/FeesView.vue'), meta: { title: '费率管理', perm: 'fee:view' } },
      { path: 'promotions', name: 'promotions', component: () => import('@/views/PromotionsView.vue'), meta: { title: '推广奖励', perm: 'account:view' } },
      { path: 'withdrawals', name: 'withdrawals', component: () => import('@/views/WithdrawalsView.vue'), meta: { title: '提现管理', perm: 'withdrawal:view' } },
      { path: 'tickets', name: 'tickets', component: () => import('@/views/TicketsView.vue'), meta: { title: '工单管理', perm: 'ticket:view' } },
      { path: 'appeals', name: 'appeals', component: () => import('@/views/AppealsView.vue'), meta: { title: '申诉管理', perm: 'appeal:view' } },
      { path: 'risk', name: 'risk', component: () => import('@/views/RiskView.vue'), meta: { title: '风控管理', perm: 'risk:view' } },
      { path: 'admins', name: 'admins', component: () => import('@/views/AdminsView.vue'), meta: { title: '管理员管理', perm: 'system:admin' } },
      { path: 'roles', name: 'roles', component: () => import('@/views/RolesView.vue'), meta: { title: '角色权限', perm: 'system:role' } },
      { path: 'permissions', name: 'permissions', component: () => import('@/views/PermissionsView.vue'), meta: { title: '权限点', perm: 'system:role' } },
      { path: 'announcements', name: 'announcements', component: () => import('@/views/AnnouncementsView.vue'), meta: { title: '公告管理', perm: 'system:announcement' } },
      { path: 'logs', name: 'logs', component: () => import('@/views/LogsView.vue'), meta: { title: '操作日志', perm: 'system:log' } },
      { path: 'settings', name: 'settings', component: () => import('@/views/SettingsView.vue'), meta: { title: '系统设置', perm: 'system:config' } },
    ],
  },
  { path: '/', redirect: '/admin/dashboard' },
  { path: '/:pathMatch(.*)*', redirect: '/admin/dashboard' },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to) => {
  const auth = useAuthStore()

  if (to.meta.public) {
    if (auth.token && to.path === '/admin/login') return '/admin/dashboard'
    return true
  }

  if (!auth.token) {
    return { path: '/admin/login', query: { redirect: to.fullPath } }
  }

  const perm = to.meta.perm
  if (perm && !auth.hasPerm(perm)) {
    ElMessage.warning('无权访问该页面')
    return '/admin/dashboard'
  }

  return true
})

router.afterEach((to) => {
  const title = to.meta.title
  document.title = title ? `${title} · LX 平台管理后台` : 'LX 平台管理后台'
})

export default router
