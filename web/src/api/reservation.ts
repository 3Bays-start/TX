import http from './http'

export interface ReservationPayload {
  order_id: number
}

export interface Reservation {
  id: number
  order_id?: number
  product_name?: string
  amount?: string
  status?: string
  reservation_time?: string
  created_at?: string
}

export interface MatchingStatus {
  order_id: number
  status: string
  matched_amount?: string
  target_amount?: string
  remaining_amount?: string
  message?: string
}

export function createReservation(payload: ReservationPayload): Promise<Reservation> {
  return http.post<Reservation>('/reservations', payload)
}

export async function getReservations(): Promise<Reservation[]> {
  const res = await http.get<{ items?: Reservation[] } | Reservation[]>('/reservations')
  return Array.isArray(res) ? res : (res.items ?? [])
}

export function getMatchingStatus(order_id: number): Promise<MatchingStatus> {
  return http.get<MatchingStatus>(`/reservations/matching/status/${order_id}`)
}