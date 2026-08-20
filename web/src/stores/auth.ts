import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(localStorage.getItem('lx_token'))

  function setToken(value: string) {
    token.value = value
    localStorage.setItem('lx_token', value)
  }

  function clearToken() {
    token.value = null
    localStorage.removeItem('lx_token')
  }

  return { token, setToken, clearToken }
})
