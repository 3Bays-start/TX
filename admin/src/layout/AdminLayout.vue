<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { changeAdminPassword } from '@/api/admin'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()
const isCollapse = ref(false)

const pwdVisible = ref(false)
const pwdSubmitting = ref(false)
const pwdForm = reactive({
  old_password: '',
  new_password: '',
  confirm: '',
})

interface MenuNode {
  title: string
  icon?: string
  path?: string
  perm?: string
  children?: MenuNode[]
}

const menus: MenuNode[] = [
  { title: '数据概览', icon: 'Odometer', path: '/admin/dashboard' },
  {
    title: '用户',
    icon: 'User',
    children: [
      { title: '用户管理', path: '/admin/users', perm: 'user:view' },
    ],
  },
  {
    title: '订单',
    icon: 'Document',
    children: [
      { title: '订单管理', path: '/admin/orders', perm: 'order:view' },
      { title: '撮合管理', path: '/admin/matching', perm: 'order:view' },
    ],
  },
  {
    title: '财务',
    icon: 'Wallet',
    children: [
      { title: '账户查询', path: '/admin/accounts', perm: 'account:view' },
      { title: '交易流水', path: '/admin/transactions', perm: 'transaction:view' },
      { title: '费率管理', path: '/admin/fees', perm: 'fee:view' },
      { title: '推广奖励', path: '/admin/promotions', perm: 'account:view' },
      { title: '提现管理', path: '/admin/withdrawals', perm: 'withdrawal:view' },
    ],
  },
  {
    title: '客服',
    icon: 'Service',
    children: [
      { title: '工单管理', path: '/admin/tickets', perm: 'ticket:view' },
      { title: '申诉管理', path: '/admin/appeals', perm: 'appeal:view' },
    ],
  },
  { title: '风控', icon: 'Warning', path: '/admin/risk', perm: 'risk:view' },
  {
    title: '系统',
    icon: 'Setting',
    children: [
      { title: '管理员管理', path: '/admin/admins', perm: 'system:admin' },
      { title: '角色权限', path: '/admin/roles', perm: 'system:role' },
      { title: '权限点', path: '/admin/permissions', perm: 'system:role' },
      { title: '公告管理', path: '/admin/announcements', perm: 'system:announcement' },
      { title: '操作日志', path: '/admin/logs', perm: 'system:log' },
      { title: '系统设置', path: '/admin/settings', perm: 'system:config' },
    ],
  },
]

const visibleMenus = computed<MenuNode[]>(() =>
  menus
    .map((m) =>
      m.children
        ? { ...m, children: m.children.filter((c) => auth.hasPerm(c.perm)) }
        : m,
    )
    .filter((m) => !m.children || m.children.length > 0),
)

const activeMenu = computed(() => {
  const path = route.path
  if (path.startsWith('/admin/users')) return '/admin/users'
  if (path.startsWith('/admin/orders')) return '/admin/orders'
  return path
})

function handleCommand(command: string) {
  if (command === 'logout') {
    ElMessageBox.confirm('确定退出登录吗？', '提示', { type: 'warning' })
      .then(() => {
        auth.logout()
        router.push('/admin/login')
      })
      .catch(() => {})
  } else if (command === 'password') {
    pwdForm.old_password = ''
    pwdForm.new_password = ''
    pwdForm.confirm = ''
    pwdVisible.value = true
  }
}

async function submitPassword() {
  if (!pwdForm.old_password) {
    ElMessage.warning('请输入原密码')
    return
  }
  if (pwdForm.new_password.length < 8) {
    ElMessage.warning('新密码至少 8 位')
    return
  }
  if (pwdForm.new_password !== pwdForm.confirm) {
    ElMessage.warning('两次输入的新密码不一致')
    return
  }
  pwdSubmitting.value = true
  try {
    await changeAdminPassword({
      old_password: pwdForm.old_password,
      new_password: pwdForm.new_password,
    })
    ElMessage.success('密码已修改')
    pwdVisible.value = false
  } catch {
    // 错误提示已由拦截器统一弹出
  } finally {
    pwdSubmitting.value = false
  }
}

onMounted(() => {
  auth.refreshMe().catch(() => {})
})
</script>

<template>
  <el-container class="admin-layout">
    <el-aside :width="isCollapse ? '64px' : '220px'" class="admin-aside">
      <div class="logo" @click="router.push('/admin/dashboard')">
        <span class="logo-icon">LX</span>
        <span v-if="!isCollapse" class="logo-text">LX 平台 · 管理后台</span>
      </div>
      <el-menu
        :default-active="activeMenu"
        :collapse="isCollapse"
        :collapse-transition="false"
        router
        class="admin-menu"
        background-color="#001529"
        text-color="rgba(255,255,255,0.72)"
        active-text-color="#ffffff"
      >
        <template v-for="item in visibleMenus" :key="item.title">
          <el-sub-menu v-if="item.children" :index="item.title">
            <template #title>
              <el-icon v-if="item.icon"><component :is="item.icon" /></el-icon>
              <span>{{ item.title }}</span>
            </template>
            <el-menu-item v-for="child in item.children" :key="child.path" :index="child.path">
              <span>{{ child.title }}</span>
            </el-menu-item>
          </el-sub-menu>
          <el-menu-item v-else :index="item.path">
            <el-icon v-if="item.icon"><component :is="item.icon" /></el-icon>
            <template #title><span>{{ item.title }}</span></template>
          </el-menu-item>
        </template>
      </el-menu>
    </el-aside>

    <el-container class="admin-body">
      <el-header class="admin-header" height="56px">
        <el-icon class="collapse-btn" @click="isCollapse = !isCollapse">
          <Expand v-if="isCollapse" />
          <Fold v-else />
        </el-icon>
        <div class="header-title">{{ route.meta.title || '' }}</div>
        <div class="header-right">
          <el-dropdown @command="handleCommand">
            <span class="admin-user">
              <el-avatar :size="28" class="admin-avatar">
                {{ (auth.admin?.nickname || auth.admin?.username || 'A').slice(0, 1) }}
              </el-avatar>
              <span class="admin-name">{{ auth.admin?.nickname || auth.admin?.username }}</span>
              <el-tag v-if="auth.isSuper" size="small" type="warning" effect="dark">超管</el-tag>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="password">修改密码</el-dropdown-item>
                <el-dropdown-item divided command="logout">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>

      <el-dialog v-model="pwdVisible" title="修改密码" width="420px" :close-on-click-modal="false">
        <el-form label-width="90px" @submit.prevent>
          <el-form-item label="原密码">
            <el-input v-model="pwdForm.old_password" type="password" show-password placeholder="请输入原密码" />
          </el-form-item>
          <el-form-item label="新密码">
            <el-input v-model="pwdForm.new_password" type="password" show-password placeholder="至少 8 位" />
          </el-form-item>
          <el-form-item label="确认新密码">
            <el-input v-model="pwdForm.confirm" type="password" show-password placeholder="再次输入新密码" />
          </el-form-item>
        </el-form>
        <template #footer>
          <el-button @click="pwdVisible = false">取消</el-button>
          <el-button type="primary" :loading="pwdSubmitting" @click="submitPassword">确定</el-button>
        </template>
      </el-dialog>
      <el-main class="admin-main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<style scoped>
.admin-layout {
  height: 100%;
}

.admin-aside {
  background-color: #001529;
  display: flex;
  flex-direction: column;
  transition: width 0.2s;
}

.logo {
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: #fff;
  cursor: pointer;
  flex-shrink: 0;
}

.logo-icon {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  background: linear-gradient(135deg, #409eff, #67c23a);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 14px;
}

.logo-text {
  font-size: 15px;
  font-weight: 600;
  white-space: nowrap;
}

.admin-menu {
  border-right: none;
  flex: 1;
  overflow-y: auto;
}

.admin-menu :deep(.el-menu-item),
.admin-menu :deep(.el-sub-menu__title) {
  height: 46px;
  line-height: 46px;
}

.admin-menu :deep(.el-menu-item.is-active) {
  background-color: #409eff;
}

.admin-body {
  min-width: 0;
}

.admin-header {
  background: #fff;
  display: flex;
  align-items: center;
  gap: 12px;
  box-shadow: 0 1px 4px rgba(0, 21, 41, 0.08);
  position: relative;
  z-index: 10;
}

.collapse-btn {
  font-size: 20px;
  cursor: pointer;
  color: #606266;
}

.header-title {
  font-size: 15px;
  font-weight: 600;
  color: #303133;
}

.header-right {
  margin-left: auto;
}

.admin-user {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  outline: none;
}

.admin-avatar {
  background: #409eff;
  color: #fff;
  font-size: 13px;
}

.admin-name {
  font-size: 14px;
  color: #303133;
}

.admin-main {
  background: #f0f2f5;
  padding: 0;
  overflow-y: auto;
}
</style>
