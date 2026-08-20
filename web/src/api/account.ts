import http from './http'
import type { PageResult } from './http'

export interface AccountSummary {
  available: string
  frozen: string
  pending: string
  currency?: string
}

export interface TransactionRecord {
  id: number
  business_type?: string
  direction?: string
  amount: string
  balance?: string
  remark?: string
  created_at?: string
}

export function getAccounts(): Promise<AccountSummary> {
  return http.get<AccountSummary>('/accounts')
}

export function getTransactions(params: {
  business_type?: string
  page?: number
  page_size?: number
}): Promise<PageResult<TransactionRecord>> {
  return http.get<PageResult<TransactionRecord>>('/accounts/transactions', { params })
}
