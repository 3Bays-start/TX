import http from './http'

export interface CreditLevelItem {
  name: string
  code: string
  min_orders: number
  description?: string
}

export interface CreditInfo {
  completed_order_count: number
  current: CreditLevelItem
  next: CreditLevelItem | null
  progress: number
  need: number
  levels: CreditLevelItem[]
}

export function getMyCredit(): Promise<CreditInfo> {
  return http.get<CreditInfo>('/credit/level')
}