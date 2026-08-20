import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { ADMIN_INFO_KEY, TOKEN_KEY } from '@/api/http'
import { adminLogin as apiLogin, adminMe as apiMe } from '@/api/admin'
import type { AdminInfo, LoginResult } from '@/api/types'

function readAdminInfo(): AdminInfo | null {
  try {
    const raw = localStorage.getItem(ADMIN_INFO_KEY)
    return raw ? (JSON.parse(raw) as AdminInfo) : null
  } catch {
    return null
  }
}

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string>(localStorage.getItem(TOKEN_KEY) || '')
  const admin = ref<AdminInfo | null>(readAdminInfo())
  const permissions = ref<string[]>([])

  const isSuper = computed(() => Boolean(admin.value?.is_super || admin.value?.role_code === 'SUPER_ADMIN'))

  function setSession(result: LoginResult) {
    token.value = result.access_token
    permissions.value = result.permissions
    admin.value = {
      id: result.admin.id,
      username: result.admin.username,
      nickname: result.admin.nickname,
      role_code: result.admin.is_super ? 'SUPER_ADMIN' : 'ADMIN',
      is_super: result.admin.is_super,
      permissions: result.permissions,
    }
    localStorage.setItem(TOKEN_KEY, result.access_token)
    localStorage.setItem(ADMIN_INFO_KEY, JSON.stringify(admin.value))
  }

  function hasPerm(code?: string): boolean {
    if (!code) return true
    if (isSuper.value) return true
    return permissions.value.includes(code)
  }

  async function login(username: string, password: string) {
    const result = await apiLogin({ username, password })
    setSession(result)
  }

  async function refreshMe() {
    if (!token.value) return
    const me = await apiMe()
    admin.value = me
    permissions.value = me.permissions
    localStorage.setItem(ADMIN_INFO_KEY, JSON.stringify(me))
  }

  function logout() {
    token.value = ''
    admin.value = null
    permissions.value = []
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(ADMIN_INFO_KEY)
  }

  return { token, admin, permissions, isSuper, login, logout, hasPerm, refreshMe }
})
