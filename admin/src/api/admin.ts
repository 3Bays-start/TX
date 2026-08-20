import { get, post, put } from './http'
import type {
  AccountInfo,
  AdminInfo,
  AdminUser,
  Announcement,
  ApiPage,
  Appeal,
  DashboardData,
  FeeRecord,
  FeeRule,
  InviteCode,
  LoginResult,
  MatchingAutoResult,
  MatchingItem,
  MatchingJob,
  MatchingManualResult,
  OperationLog,
  OrderDetail,
  OrderItem,
  Permission,
  PromotionItem,
  RiskEvent,
  Role,
  SwitchLoginResult,
  Ticket,
  TransactionItem,
  UserDetail,
  UserItem,
  WithdrawalItem,
} from './types'

export const TOKEN_KEY = 'lx_admin_token'
export const ADMIN_INFO_KEY = 'lx_admin_info'

// ===== 认证 =====

export const adminLogin = (data: { username: string; password: string }) =>
  post<LoginResult>('/admin/login', data)

export const adminMe = () => get<AdminInfo>('/admin/me')

export const changeAdminPassword = (data: { old_password: string; new_password: string }) =>
  post<null>('/admin/me/password', data)

// ===== Dashboard =====

export const fetchDashboard = () => get<DashboardData>('/admin/dashboard')

// ===== 用户管理 =====

export interface UserQuery {
  user_id?: number
  phone?: string
  keyword?: string
  status?: string
  risk_level?: string
  page: number
  page_size: number
}

export const listUsers = (params: UserQuery) => get<ApiPage<UserItem>>('/admin/users', params)

export const switchLoginUser = (userId: number) =>
  post<SwitchLoginResult>(`/admin/users/${userId}/switch-login`)

export const getUserDetail = (id: number) => get<UserDetail>(`/admin/users/${id}`)

export const freezeUser = (id: number, data: { reason?: string }) =>
  post<null>(`/admin/users/${id}/freeze`, data)

export const unfreezeUser = (id: number, data: { reason?: string }) =>
  post<null>(`/admin/users/${id}/unfreeze`, data)

export const adjustUserBalance = (id: number, data: { amount: string; reason?: string }) =>
  post<null>(`/admin/users/${id}/adjust`, data)

// ===== 订单管理 =====

export interface OrderQuery {
  order_no?: string
  status?: string
  order_type?: string
  user_id?: number
  page: number
  page_size: number
}

export const listOrders = (params: OrderQuery) => get<ApiPage<OrderItem>>('/admin/orders', params)

export const getOrderDetail = (id: number) => get<OrderDetail>(`/admin/orders/${id}`)

// ===== 撮合管理 =====

export const listMatching = (params: { status?: string; page: number; page_size: number }) =>
  get<ApiPage<MatchingItem>>('/admin/matching', params)

export const listMatchingJobs = (params: { page: number; page_size: number }) =>
  get<{ items: MatchingJob[]; total: number }>('/admin/matching/jobs', params)

export const manualMatchBatch = (payload: {
  buy_order_ids: number[]
  sell_order_ids: number[]
  reason?: string
}) => post<MatchingManualResult>('/admin/matching/manual', payload)

export const autoMatch = () => post<MatchingAutoResult>('/admin/matching/auto')

// ===== 财务 =====

export const getUserAccount = (userId: number) => get<AccountInfo>(`/admin/accounts/${userId}`)

export interface TransactionQuery {
  user_id?: number
  business_type?: string
  page: number
  page_size: number
}

export const listTransactions = (params: TransactionQuery) =>
  get<{ items: TransactionItem[]; total: number }>('/admin/transactions', params)

export const listWithdrawals = (params: { status?: string; page: number; page_size: number }) =>
  get<{ items: WithdrawalItem[]; total: number }>('/admin/withdrawals', params)

export const reviewWithdrawal = (
  id: number,
  data: { approve: boolean; reason?: string },
) => post<null>(`/admin/withdrawals/${id}/review`, data)

export const completeWithdrawal = (id: number) => post<null>(`/admin/withdrawals/${id}/complete`)

export const listFeeRules = () => get<{ items: FeeRule[] }>('/admin/fees')

export const updateFeeRule = (
  feeType: string,
  data: { name?: string; rate?: string; min_fee?: string; max_fee?: string; status?: string },
) => put<null>(`/admin/fees/${feeType}`, data)

export const listFeeRecords = (params: { page: number; page_size: number }) =>
  get<{ items: FeeRecord[]; total: number }>('/admin/fees/records', params)

export const listPromotions = (params: { page: number; page_size: number }) =>
  get<{ items: PromotionItem[]; total: number }>('/admin/promotions', params)

// ===== 风控 =====

export const listRiskEvents = (params: { status?: string; page: number; page_size: number }) =>
  get<{ items: RiskEvent[]; total: number }>('/admin/risk/events', params)

export const reviewRiskEvent = (
  id: number,
  data: { approve: boolean; action?: string; reason?: string },
) => post<null>(`/admin/risk/events/${id}/review`, data)

// ===== 客服 =====

export const listTickets = (params: { status?: string; page: number; page_size: number }) =>
  get<{ items: Ticket[]; total: number }>('/admin/tickets', params)

export const replyTicket = (id: number, data: { content: string; attachments?: string }) =>
  post<null>(`/admin/tickets/${id}/reply`, data)

export const closeTicket = (id: number) => post<null>(`/admin/tickets/${id}/close`)

// ===== 申诉 =====

export const listAppeals = (params: { status?: string; page: number; page_size: number }) =>
  get<{ items: Appeal[]; total: number }>('/admin/appeals', params)

export const processAppeal = (
  id: number,
  data: { approve: boolean; result?: string },
) => post<null>(`/admin/appeals/${id}/process`, data)

// ===== RBAC =====

export const listAdmins = () => get<{ items: AdminUser[] }>('/admin/admins')

export const createAdmin = (data: {
  username: string
  password: string
  nickname?: string
  role_code?: string
  role_ids?: number[]
}) => post<null>('/admin/admins', data)

export const updateAdmin = (
  id: number,
  data: { nickname?: string; password?: string; status?: string; role_ids?: number[] },
) => put<null>(`/admin/admins/${id}`, data)

export const listRoles = () => get<{ items: Role[] }>('/admin/roles')

export const createRole = (data: {
  code: string
  name: string
  description?: string
  permission_codes: string[]
}) => post<null>('/admin/roles', data)

export const updateRole = (
  id: number,
  data: { name?: string; description?: string; permission_codes?: string[] },
) => put<null>(`/admin/roles/${id}`, data)

export const listPermissions = () => get<{ items: Permission[] }>('/admin/permissions')

// ===== 日志 =====

export const listLogs = (params: { page: number; page_size: number }) =>
  get<{ items: OperationLog[]; total: number }>('/admin/logs', params)

// ===== 邀请码 =====

export const createSystemInvites = (data: { count?: number; expires_in_days?: number }) =>
  post<{ items: InviteCode[] }>('/admin/invites', data)

// ===== 公告 =====

export const listAnnouncements = () => get<{ items: Announcement[] }>('/admin/announcements')

export const createAnnouncement = (data: { title: string; content?: string; type?: string }) =>
  post<{ id: number }>('/admin/announcements', data)
