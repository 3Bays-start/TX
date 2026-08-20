import http from './http'
import type { PageResult } from './http'

export interface UserProfile {
  id: number
  username: string
  phone?: string
  nickname: string
  avatar: string
  gender?: string
  email?: string
  region?: string
  bio?: string
  status?: string
  credit_level_name?: string
  credit_level_code?: string
  completed_order_count?: number
  created_at: string
}

export interface UpdateProfilePayload {
  nickname?: string
  gender?: string
  email?: string
  region?: string
  bio?: string
  avatar?: string
}

export interface TeamSummary {
  total_team?: number
  direct_count?: number
  active_count?: number
  team_order_count?: number
  team_order_amount?: string
}

export interface TeamMember {
  user_id: number
  username: string
  nickname: string
  created_at?: string
}

export interface SwitchableMember {
  user_id: number
  username: string
  nickname: string
  allow_parent_switch: boolean
}

export function getMe(): Promise<UserProfile> {
  return http.get<UserProfile>('/users/me')
}

export function updateProfile(payload: UpdateProfilePayload): Promise<UserProfile> {
  return http.put<UserProfile>('/users/me/profile', payload)
}

export function changePassword(payload: { old_password: string; new_password: string }): Promise<unknown> {
  return http.post('/users/me/password', payload)
}

export function getTeamSummary(): Promise<TeamSummary> {
  return http.get<TeamSummary>('/users/team/summary')
}

export function getTeam(params: { page: number; page_size: number }): Promise<PageResult<TeamMember>> {
  return http.get<PageResult<TeamMember>>('/users/team', { params })
}

export async function getSwitchable(): Promise<SwitchableMember[]> {
  const res = await http.get<{ items: SwitchableMember[] }>('/users/team/switchable')
  return res.items ?? []
}