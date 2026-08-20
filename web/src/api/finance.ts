import http from './http'
import type { PageResult } from './http'

export interface WithdrawalPayload {
  amount: string
  usdt_address: string
}

export interface Withdrawal extends WithdrawalPayload {
  id: number
  withdrawal_no?: string
  status?: string
  review_reason?: string
  created_at?: string
}

export interface FeeInfo {
  withdrawal_fee?: string
  service_fee?: string
}

export interface PromotionRecord {
  id: number
  invited_phone?: string
  type?: string
  amount?: string
  reward?: string
  created_at?: string
}

export function getFees(): Promise<FeeInfo> {
  return http.get<FeeInfo>('/fees')
}

export function createWithdrawal(payload: WithdrawalPayload): Promise<Withdrawal> {
  return http.post<Withdrawal>('/withdrawals', payload)
}

export function getWithdrawals(params: {
  status?: string
  page?: number
  page_size?: number
}): Promise<PageResult<Withdrawal>> {
  return http.get<PageResult<Withdrawal>>('/withdrawals', { params })
}

export function getPromotionRecords(params: {
  page?: number
  page_size?: number
}): Promise<PageResult<PromotionRecord>> {
  return http.get<PageResult<PromotionRecord>>('/promotion/records', { params })
}
