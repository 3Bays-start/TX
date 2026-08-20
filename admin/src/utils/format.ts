export function formatAmount(value: string | number | null | undefined): string {
  if (value === null || value === undefined || value === '') return '¥0.00'
  const n = Number(value)
  if (Number.isNaN(n)) return String(value)
  return (
    '¥' +
    n.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
  )
}

export function formatDateTime(value: string | null | undefined): string {
  if (!value) return '-'
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return value
  const p = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`
}

export const TAG_TYPES: Record<string, 'success' | 'info' | 'warning' | 'danger' | 'primary'> = {
  ACTIVE: 'success',
  FROZEN: 'danger',
  DISABLED: 'info',
  APPROVED: 'success',
  REJECTED: 'danger',
  PENDING: 'warning',
  NONE: 'info',
  REVIEWING: 'warning',
  LOW: 'success',
  MEDIUM: 'warning',
  HIGH: 'danger',
  WAITING_MATCH: 'warning',
  PARTIAL_MATCHED: 'warning',
  FULL_MATCHED: 'success',
  COMPLETED: 'success',
  EXPIRED: 'info',
  DISPUTED: 'danger',
  RISK_REVIEW: 'danger',
  CANCELLED: 'info',
  RUNNING: 'warning',
  SUCCESS: 'success',
  FAILED: 'danger',
  OPEN: 'success',
  CLOSED: 'info',
  RESOLVED: 'success',
  DISMISSED: 'info',
  BUY: 'primary',
  SELL: 'warning',
  INCOME: 'success',
  EXPENSE: 'danger',
  ON: 'success',
  OFF: 'info',
  NORMAL: 'success',
  IMPORTANT: 'warning',
  NOTICE: 'info',
}

export function tagType(status: string): 'success' | 'info' | 'warning' | 'danger' | 'primary' {
  return TAG_TYPES[status] ?? 'info'
}

export const STATUS_TEXT: Record<string, string> = {
  ACTIVE: '正常',
  FROZEN: '已冻结',
  DISABLED: '已禁用',
  APPROVED: '已通过',
  REJECTED: '已拒绝',
  PENDING: '待处理',
  REVIEWING: '审核中',
  NONE: '未认证',
  LOW: '低风险',
  MEDIUM: '中风险',
  HIGH: '高风险',
  CREATED: '已创建',
  WAITING_PAYMENT: '待支付',
  WAITING_MATCH: '待撮合',
  PARTIAL_MATCHED: '部分撮合',
  FULL_MATCHED: '已撮合',
  COMPLETED: '已完成',
  EXPIRED: '已过期',
  DISPUTED: '争议中',
  RISK_REVIEW: '风控复核',
  CANCELLED: '已取消',
  PROCESSING: '服务中',
  RUNNING: '执行中',
  SUCCESS: '成功',
  FAILED: '失败',
  OPEN: '进行中',
  CLOSED: '已关闭',
  RESOLVED: '已处理',
  DISMISSED: '已忽略',
  WAITING_USER: '待用户',
  BUY: '买入',
  SELL: '卖出',
  SERVICE: '服务订单',
  INCOME: '收入',
  EXPENSE: '支出',
  ON: '上架',
  OFF: '下架',
  NORMAL: '普通',
  IMPORTANT: '重要',
  NOTICE: '通知',
  PAID: '已支付',
}

export function statusText(status: string): string {
  return STATUS_TEXT[status] ?? status
}
