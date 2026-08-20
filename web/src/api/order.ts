import http from './http'
import type { PageResult } from './http'

export type OrderType = 'BUY' | 'SELL'

export interface CreateOrderPayload {
  order_type?: OrderType
  amount?: string
  reservation_time?: string
  remark?: string
}

export interface Order {
  id: number
  order_no?: string
  order_type?: OrderType
  product_name?: string
  total_amount?: string
  service_fee?: string
  payable_amount?: string
  matched_amount?: string
  unit_price?: string
  status?: string
  remark?: string
  created_at?: string
  updated_at?: string
}

export interface OrderStatusLog {
  id?: number
  from_status?: string
  to_status: string
  note?: string
  created_at?: string
}

export interface MatchItem {
  id?: number
  matched_order_no?: string
  amount?: string
  quantity?: number
  created_at?: string
}

export interface OrderDetail extends Order {
  status_logs?: OrderStatusLog[]
  matches?: MatchItem[]
  target_amount?: string
  matched_amount?: string
  remaining_amount?: string
  proof_urls?: string[]
  proof_submitted_at?: string
}

export interface OrderMatchInfo {
  order_id: number
  target_amount: string
  matched_amount: string
  remaining_amount: string
  status: string
  matches: MatchItem[]
}

export function createOrder(payload: CreateOrderPayload): Promise<Order> {
  return http.post<Order>('/orders', payload)
}

export function getOrders(params: { status?: string; page?: number; page_size?: number }): Promise<PageResult<Order>> {
  return http.get<PageResult<Order>>('/orders', { params })
}

export function getOrder(id: number): Promise<OrderDetail> {
  return http.get<OrderDetail>(`/orders/${id}`)
}

export function payOrder(id: number): Promise<unknown> {
  return http.post(`/orders/${id}/pay`)
}

export function cancelOrder(id: number): Promise<unknown> {
  return http.post(`/orders/${id}/cancel`)
}

export function getOrderMatch(id: number): Promise<OrderMatchInfo> {
  return http.get<OrderMatchInfo>(`/orders/${id}/match`)
}

export function uploadFile(file: File): Promise<{ url: string; filename: string }> {
  const form = new FormData()
  form.append('file', file)
  return http.post<{ url: string; filename: string }>('/upload', form)
}

export function submitProof(id: number, urls: string[]): Promise<OrderDetail> {
  return http.post<OrderDetail>(`/orders/${id}/proof`, { urls })
}
