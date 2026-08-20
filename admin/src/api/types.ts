export interface ApiPage<T> {
  items: T[]
  total: number
  page?: number
  page_size?: number
}

export interface LoginResult {
  access_token: string
  expires_in: number
  admin: { id: number; username: string; nickname: string; is_super: boolean }
  permissions: string[]
}

export interface SwitchLoginResult {
  access_token: string
  refresh_token: string
  expires_in: number
}

export interface AdminInfo {
  id: number
  username: string
  nickname: string
  role_code: string
  is_super: boolean
  permissions: string[]
}

export interface DashboardData {
  user_total: number
  user_today: number
  active_users: number
  order_total: number
  order_today: number
  waiting_match: number
  matching: number
  abnormal_orders: number
  appeal_pending: number
  withdrawal_pending: number
  service_fee_total: string
  charts: { user_growth: number[]; order_trend: number[] }
}

export interface UserItem {
  id: number
  phone: string
  nickname: string
  status: string
  risk_level: string
  completed_order_count: number
  credit_level_name: string
  created_at: string | null
  last_login_at: string | null
}

export interface UserDetail {
  id: number
  phone: string
  nickname: string
  avatar: string
  status: string
  risk_level: string
  register_ip: string
  last_login_at: string | null
  created_at: string | null
  credit_level_name: string
  completed_order_count: number
  account: { available_amount: string; frozen_amount: string }
}

export interface UserInfo {
  user_nickname: string
  user_username: string
  user_phone: string
}

export interface OrderItem extends UserInfo {
  id: number
  order_no: string
  user_id: number
  order_type: string
  product_name: string
  total_amount: string
  service_fee: string
  matched_amount: string
  status: string
  created_at: string | null
}

export interface OrderStatusLog {
  from_status: string
  to_status: string
  reason: string
  created_at: string | null
}

export interface OrderMatch {
  match_no: string
  buyer_order_id: number
  seller_order_id: number
  seller_user_id: number
  seller_nickname: string
  seller_phone: string
  match_amount: string
  status: string
}

export interface OrderDetail extends UserInfo {
  id: number
  order_no: string
  user_id: number
  order_type: string
  product_name: string
  total_amount: string
  service_fee: string
  payable_amount: string
  matched_amount: string
  status: string
  reservation_time: string | null
  remark: string
  proof_urls: string[]
  proof_submitted_at: string | null
  created_at: string | null
  status_logs: OrderStatusLog[]
  matches: OrderMatch[]
}

export interface MatchingItem extends UserInfo {
  id: number
  order_no: string
  user_id: number
  order_type: string
  target_amount: string
  matched_amount: string
  remaining_amount: string
  status: string
  created_at: string | null
}

export interface MatchingJob {
  job_id: string
  start_time: string | null
  end_time: string | null
  processed_count: number
  success_count: number
  failed_count: number
  status: string
}

export interface AccountInfo {
  account_no: string
  available_amount: string
  frozen_amount: string
  pending_amount: string
}

export interface TransactionItem extends UserInfo {
  transaction_no: string
  user_id: number
  business_type: string
  amount: string
  before_balance: string
  after_balance: string
  direction: string
  reason: string
  created_at: string | null
}

export interface WithdrawalItem extends UserInfo {
  id: number
  withdrawal_no: string
  user_id: number
  amount: string
  actual_amount: string
  usdt_address: string
  status: string
  review_reason: string
  created_at: string | null
}

export interface FeeRule {
  id: number
  fee_type: string
  name: string
  rate: string
  min_fee: string
  max_fee: string
  status: string
  effective_at: string | null
}

export interface FeeRecord {
  fee_no: string
  order_id: number
  fee_type: string
  base_amount: string
  rate: string
  fee_amount: string
  created_at: string | null
}

export interface PromotionItem {
  record_no: string
  source_user_id: number
  source_user_nickname: string
  source_user_username: string
  source_user_phone: string
  source_order_id: number
  beneficiary_user_id: number
  beneficiary_user_nickname: string
  beneficiary_user_username: string
  beneficiary_user_phone: string
  reward_amount: string
  status: string
  created_at: string | null
}

export interface RiskEvent extends UserInfo {
  id: number
  event_no: string
  user_id: number
  rule_code: string
  level: string
  action: string
  detail: string
  status: string
  created_at: string | null
}

export interface Ticket extends UserInfo {
  id: number
  ticket_no: string
  user_id: number
  category: string
  title: string
  priority: string
  status: string
  created_at: string | null
}

export interface Appeal extends UserInfo {
  id: number
  appeal_no: string
  user_id: number
  order_id: number
  subject: string
  status: string
  result: string
  created_at: string | null
}

export interface AdminUser {
  id: number
  username: string
  nickname: string
  role_code: string
  status: string
  is_super: boolean
  last_login_at: string | null
}

export interface Role {
  id: number
  code: string
  name: string
  description: string
  is_system: boolean
  permission_codes: string[]
}

export interface Permission {
  code: string
  name: string
  group: string
  description: string
}

export interface OperationLog {
  id: number
  operator_type: string
  operator_id: number
  action: string
  module: string
  target_type: string
  target_id: number
  reason: string
  ip: string
  request_id: string
  created_at: string | null
}

export interface Announcement {
  id: number
  title: string
  content: string
  type: string
  status: string
  published_at: string | null
}

export interface InviteCode {
  id: number
  code: string
}

export interface MatchingManualResult {
  matched: number
  buy_orders: number
  sell_orders: number
}

export interface MatchingAutoResult {
  processed: number
  matched: number
  failed: number
}
