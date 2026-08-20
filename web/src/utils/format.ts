export function formatMoney(amount?: string | number | null): string {
  if (amount === undefined || amount === null || amount === '') return '¥0'
  const num = Number(amount)
  if (Number.isNaN(num)) return `¥${amount}`
  return `¥${num.toLocaleString('zh-CN', { maximumFractionDigits: 2 })}`
}

export function formatTime(value?: string | null): string {
  if (!value) return '-'
  return value.replace('T', ' ').slice(0, 16)
}

export type TagType = 'primary' | 'success' | 'danger' | 'warning' | 'default'

export function statusTagType(status?: string | null): TagType {
  const s = status ?? ''
  if (/PAID|MATCHED|SUCCESS|COMPLETED|DONE|REVIEWED|APPROVED|RESOLVED/.test(s)) return 'success'
  if (/CANCEL|FAILED|REJECTED|DENIED|DISABLED|INACTIVE/.test(s)) return 'danger'
  if (/WAITING|PENDING|PROCESSING|REVIEW|RESERVED|OPEN/.test(s)) return 'warning'
  return 'default'
}

export const STATUS_TEXT: Record<string, string> = {
  // 订单
  CREATED: '已创建',
  WAITING_PAYMENT: '待支付',
  PAID: '已支付',
  WAITING_MATCH: '待撮合',
  PARTIAL_MATCHED: '部分撮合',
  FULL_MATCHED: '已撮合',
  PROCESSING: '服务中',
  COMPLETED: '已完成',
  CANCELLED: '已取消',
  EXPIRED: '已过期',
  DISPUTED: '争议中',
  RISK_REVIEW: '风控复核',
  // 工单
  OPEN: '进行中',
  WAITING_USER: '待用户',
  CLOSED: '已关闭',
  // 申诉
  PENDING: '待处理',
  RESOLVED: '已处理',
  REJECTED: '已拒绝',
  // 提现
  REVIEWING: '审核中',
  APPROVED: '已通过',
  // 预约
  WAITING: '待撮合',
  MATCHED: '已撮合',
  // 邀请码
  UNUSED: '未使用',
  USED: '已使用',
  DISABLED: '已停用',
  // 实名
  NONE: '未认证',
  ACTIVE: '正常',
  FROZEN: '已冻结',
  DISABLED_ACCOUNT: '已禁用',
  // 类型
  BUY: '买入',
  SELL: '卖出',
}

export function statusText(status?: string | null): string {
  if (!status) return '-'
  return STATUS_TEXT[status] ?? status
}
