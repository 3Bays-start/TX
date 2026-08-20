import http from './http'

export interface TokenPair {
  access_token: string
  refresh_token: string
  token_type?: string
  expires_in?: number
}

export interface LoginPayload {
  username: string
  password: string
}

export interface RegisterPayload {
  username: string
  password: string
  invite_code: string
  nickname?: string
}

export interface MeInfo {
  id: number
  username: string
  phone?: string
  nickname: string
  avatar: string
  status: string
  risk_level: string
  credit_level_name: string
  credit_level_code: string
  completed_order_count: number
  created_at: string
}

export function login(payload: LoginPayload): Promise<TokenPair> {
  return http.post<TokenPair>('/auth/login', payload)
}

export function register(payload: RegisterPayload): Promise<TokenPair> {
  return http.post<TokenPair>('/auth/register', payload)
}

export function switchUser(user_id: number): Promise<TokenPair> {
  return http.post<TokenPair>('/auth/switch-user', { user_id })
}

export function refresh(refresh_token: string): Promise<TokenPair> {
  return http.post<TokenPair>('/auth/refresh', { refresh_token })
}

export function getMe(): Promise<MeInfo> {
  return http.get<MeInfo>('/auth/me')
}