import axios from 'axios'
import type { AxiosRequestConfig, AxiosResponse, InternalAxiosRequestConfig } from 'axios'

interface ApiEnvelope<T = unknown> {
  code: number
  message: string
  data: T
  requestId?: string
}

export interface PageResult<T> {
  items: T[]
  total?: number
  page?: number
  page_size?: number
}

export interface HttpClient {
  get<T = unknown>(url: string, config?: AxiosRequestConfig): Promise<T>
  post<T = unknown>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T>
  put<T = unknown>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T>
  delete<T = unknown>(url: string, config?: AxiosRequestConfig): Promise<T>
}

const instance = axios.create({
  baseURL: '/api/v1',
  timeout: 10000,
})

instance.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = localStorage.getItem('lx_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

instance.interceptors.response.use(
  (response) => {
    const res = response.data as ApiEnvelope<unknown>
    if (res.code === 0) {
      return res.data as unknown as AxiosResponse
    }
    return Promise.reject(new Error(res.message || '请求失败'))
  },
  (error) => {
    const status: number | undefined = error.response?.status
    const url: string = error.config?.url ?? ''
    if (status === 401 && url !== '/auth/login' && url !== '/auth/register') {
      localStorage.removeItem('lx_token')
      location.href = '/login'
    }
    const data = error.response?.data as { message?: unknown } | undefined
    const message = typeof data?.message === 'string' ? data.message : error.message || '网络错误'
    return Promise.reject(new Error(message))
  },
)

const http = instance as unknown as HttpClient

export default http
