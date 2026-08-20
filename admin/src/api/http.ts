import axios from 'axios'
import type { AxiosError, AxiosInstance, AxiosRequestConfig } from 'axios'
import { ElMessage } from 'element-plus'

export const TOKEN_KEY = 'lx_admin_token'
export const ADMIN_INFO_KEY = 'lx_admin_info'

export const http: AxiosInstance = axios.create({
  baseURL: '/api/v1',
  timeout: 20000,
})

http.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_KEY)
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

interface ApiEnvelope<T> {
  code: number | string
  message: string
  data: T
  requestId: string
}

http.interceptors.response.use(
  (response) => {
    const res = response.data as ApiEnvelope<unknown>
    if (res && typeof res === 'object' && 'code' in res) {
      if (res.code === 0) {
        // 统一解包：调用方通过 http.get<T, T>() 获取类型为 T 的 data
        return res.data as never
      }
      const msg = res.message || '请求失败'
      ElMessage.error(msg)
      return Promise.reject(new Error(msg))
    }
    return res as never
  },
  (error: AxiosError<ApiEnvelope<unknown>>) => {
    const status = error.response?.status
    const url = error.config?.url
    if (status === 401 && url !== '/admin/login') {
      localStorage.removeItem(TOKEN_KEY)
      localStorage.removeItem(ADMIN_INFO_KEY)
      const target = encodeURIComponent(window.location.pathname + window.location.search)
      window.location.href = `/admin/login?redirect=${target}`
      return Promise.reject(error)
    }
    const msg =
      error.response?.data?.message ||
      (status ? `请求失败（${status}）` : '网络连接失败，请稍后重试')
    ElMessage.error(msg)
    return Promise.reject(error)
  },
)

export const get = <T>(url: string, params?: object, config?: AxiosRequestConfig): Promise<T> =>
  http.get(url, { ...config, params }) as unknown as Promise<T>

export const post = <T>(url: string, data?: object, config?: AxiosRequestConfig): Promise<T> =>
  http.post(url, data, config) as unknown as Promise<T>

export const put = <T>(url: string, data?: object, config?: AxiosRequestConfig): Promise<T> =>
  http.put(url, data, config) as unknown as Promise<T>

export default http
