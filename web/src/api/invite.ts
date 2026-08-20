import http from './http'

export interface InviteCode {
  id: number
  code: string
  status: string
  expires_at: string
}

export interface InviteCodesPayload {
  count?: number
  expires_in_days?: number
}

export async function generateCodes(payload: InviteCodesPayload): Promise<InviteCode[]> {
  const res = await http.post<{ items: InviteCode[] }>('/invites/codes', payload)
  return res.items ?? []
}

export async function getCodes(): Promise<InviteCode[]> {
  const res = await http.get<{ items?: InviteCode[] } | InviteCode[]>('/invites/codes')
  return Array.isArray(res) ? res : (res.items ?? [])
}

export function disableCode(code_id: number): Promise<unknown> {
  return http.post(`/invites/codes/${code_id}/disable`)
}