import http from './http'
import type { PageResult } from './http'

export interface TicketPayload {
  category?: string
  title: string
  content: string
  order_id?: number
  priority?: string
}

export interface Ticket {
  id: number
  category?: string
  title: string
  content: string
  status?: string
  priority?: string
  created_at?: string
  updated_at?: string
}

export interface TicketMessage {
  id?: number
  sender_type: string
  content: string
  created_at?: string
}

export interface TicketDetail extends Ticket {
  messages?: TicketMessage[]
}

export interface AppealPayload {
  order_id?: number
  subject: string
  content: string
  evidence?: string
}

export interface Appeal {
  id: number
  order_id?: number
  subject: string
  content: string
  status?: string
  evidence?: string
  review_reason?: string
  created_at?: string
}

export function createTicket(payload: TicketPayload): Promise<Ticket> {
  return http.post<Ticket>('/support/tickets', payload)
}

export async function getTickets(): Promise<Ticket[]> {
  const res = await http.get<{ items?: Ticket[] } | Ticket[]>('/support/tickets')
  return Array.isArray(res) ? res : (res.items ?? [])
}

export function getTicket(id: number): Promise<TicketDetail> {
  return http.get<TicketDetail>(`/support/tickets/${id}`)
}

export function replyTicket(id: number, content: string): Promise<TicketMessage> {
  return http.post<TicketMessage>(`/support/tickets/${id}/messages`, { content })
}

export function getAppeals(params: {
  status?: string
  page?: number
  page_size?: number
}): Promise<PageResult<Appeal>> {
  return http.get<PageResult<Appeal>>('/appeals', { params })
}

export function createAppeal(payload: AppealPayload): Promise<Appeal> {
  return http.post<Appeal>('/appeals', payload)
}