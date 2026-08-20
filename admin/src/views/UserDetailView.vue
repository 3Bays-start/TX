<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import type { FormInstance, FormRules } from 'element-plus'
import { ElMessage } from 'element-plus'
import {
  adjustUserBalance,
  freezeUser,
  getUserDetail,
  getUserAccount,
  listOrders,
  listTransactions,
  unfreezeUser,
} from '@/api/admin'
import type { AccountInfo, OrderItem, TransactionItem, UserDetail } from '@/api/types'
import { useAuthStore } from '@/stores/auth'
import { formatAmount, formatDateTime, statusText, tagType } from '@/utils/format'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const userId = computed(() => Number(route.params.id))
const loading = ref(false)
const detail = ref<UserDetail | null>(null)

const activeTab = ref('transactions')
const txLoading = ref(false)
const transactions = ref<TransactionItem[]>([])
const txTotal = ref(0)
const txPage = ref(1)
const txPageSize = ref(10)

const orderLoading = ref(false)
const orders = ref<OrderItem[]>([])
const orderTotal = ref(0)
const orderPage = ref(1)
const orderPageSize = ref(10)

const account = ref<AccountInfo | null>(null)

async function loadDetail() {
  loading.value = true
  try {
    detail.value = await getUserDetail(userId.value)
    account.value = await getUserAccount(userId.value)
  } finally {
    loading.value = false
  }
}

async function loadTransactions() {
  txLoading.value = true
  try {
    const res = await listTransactions({ user_id: userId.value, page: txPage.value, page_size: txPageSize.value })
    transactions.value = res.items
    txTotal.value = res.total
  } finally {
    txLoading.value = false
  }
}

async function loadOrders() {
  orderLoading.value = true
  try {
    const res = await listOrders({ user_id: userId.value, page: orderPage.value, page_size: orderPageSize.value })
    orders.value = res.items
    orderTotal.value = res.total
  } finally {
    orderLoading.value = false
  }
}

function handleTabChange() {
  if (activeTab.value === 'transactions') loadTransactions()
  else loadOrders()
}

// ===== 冻结/解冻 =====
const statusDialog = reactive({ visible: false, type: 'freeze' as 'freeze' | 'unfreeze' })
const statusFormRef = ref<FormInstance>()
const statusForm = reactive({ reason: '' })
const statusRules: FormRules = {
  reason: [{ required: true, message: '请输入操作原因', trigger: 'blur' }],
}
const statusSubmitting = ref(false)

function openStatus(type: 'freeze' | 'unfreeze') {
  statusDialog.type = type
  statusForm.reason = ''
  statusDialog.visible = true
}

async function submitStatus() {
  if (!statusFormRef.value) return
  const valid = await statusFormRef.value.validate().catch(() => false)
  if (!valid) return
  statusSubmitting.value = true
  try {
    if (statusDialog.type === 'freeze') {
      await freezeUser(userId.value, { reason: statusForm.reason })
    } else {
      await unfreezeUser(userId.value, { reason: statusForm.reason })
    }
    ElMessage.success(statusDialog.type === 'freeze' ? '用户已冻结' : '用户已解冻')
    statusDialog.visible = false
    loadDetail()
  } finally {
    statusSubmitting.value = false
  }
}

// ===== 余额调整 =====
const adjustDialog = reactive({ visible: false })
const adjustFormRef = ref<FormInstance>()
const adjustForm = reactive({ amount: '', reason: '' })
const adjustRules: FormRules = {
  amount: [
    { required: true, message: '请输入调整金额', trigger: 'blur' },
    {
      validator: (_rule, value: string, callback) => {
        if (value !== '' && Number.isNaN(Number(value))) callback(new Error('金额格式不正确'))
        else callback()
      },
      trigger: 'blur',
    },
  ],
}
const adjustSubmitting = ref(false)

async function submitAdjust() {
  if (!adjustFormRef.value) return
  const valid = await adjustFormRef.value.validate().catch(() => false)
  if (!valid) return
  adjustSubmitting.value = true
  try {
    await adjustUserBalance(userId.value, { amount: adjustForm.amount, reason: adjustForm.reason })
    ElMessage.success('余额调整完成')
    adjustDialog.visible = false
    loadDetail()
  } finally {
    adjustSubmitting.value = false
  }
}

watch(userId, () => {
  loadDetail()
  loadTransactions()
})

onMounted(() => {
  loadDetail()
  loadTransactions()
})
</script>

<template>
  <div class="page" v-loading="loading">
    <el-page-header class="page-header" @back="router.push('/admin/users')">
      <template #content>
        <span class="page-title-inline">用户详情 #{{ userId }}</span>
      </template>
    </el-page-header>

    <template v-if="detail">
      <el-row :gutter="16">
        <el-col :xs="24" :md="14">
          <el-card shadow="never">
            <template #header><span class="card-title">基本信息</span></template>
            <el-descriptions :column="2" border>
              <el-descriptions-item label="用户">
                {{ detail.nickname || `用户${detail.id}` }}（{{ detail.phone }}）
              </el-descriptions-item>
              <el-descriptions-item label="手机号">{{ detail.phone }}</el-descriptions-item>
              <el-descriptions-item label="昵称">{{ detail.nickname || '-' }}</el-descriptions-item>
              <el-descriptions-item label="信用等级">{{ detail.credit_level_name || '-' }}（已完成 {{ detail.completed_order_count || 0 }} 笔订单）</el-descriptions-item>
              <el-descriptions-item label="账号状态">
                <el-tag :type="tagType(detail.status)" size="small">{{ statusText(detail.status) }}</el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="风险等级">
                <el-tag :type="tagType(detail.risk_level)" size="small">{{ statusText(detail.risk_level) }}</el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="注册IP">{{ detail.register_ip || '-' }}</el-descriptions-item>
              <el-descriptions-item label="注册时间">{{ formatDateTime(detail.created_at) }}</el-descriptions-item>
              <el-descriptions-item label="最近登录">{{ formatDateTime(detail.last_login_at) }}</el-descriptions-item>
            </el-descriptions>
            <div class="detail-actions">
              <el-button
                v-if="auth.hasPerm('user:freeze')"
                :type="detail.status === 'FROZEN' ? 'success' : 'danger'"
                @click="openStatus(detail.status === 'FROZEN' ? 'unfreeze' : 'freeze')"
              >
                {{ detail.status === 'FROZEN' ? '解冻用户' : '冻结用户' }}
              </el-button>
              <el-button v-if="auth.hasPerm('user:adjust')" type="warning" @click="adjustDialog.visible = true">
                调整余额
              </el-button>
            </div>
          </el-card>
        </el-col>

        <el-col :xs="24" :md="10">
          <el-card shadow="never">
            <template #header><span class="card-title">账户资金</span></template>
            <el-descriptions :column="1" border>
              <el-descriptions-item label="账户号">{{ account?.account_no || '-' }}</el-descriptions-item>
              <el-descriptions-item label="可用余额">
                <span class="money amount-available">{{ formatAmount(account?.available_amount ?? detail.account.available_amount) }}</span>
              </el-descriptions-item>
              <el-descriptions-item label="冻结余额">
                <span class="money amount-frozen">{{ formatAmount(account?.frozen_amount ?? detail.account.frozen_amount) }}</span>
              </el-descriptions-item>
              <el-descriptions-item label="待结算金额">
                <span class="money">{{ formatAmount(account?.pending_amount) }}</span>
              </el-descriptions-item>
            </el-descriptions>
          </el-card>
        </el-col>
      </el-row>

      <el-card shadow="never" class="tab-card">
        <el-tabs v-model="activeTab" @tab-change="handleTabChange">
          <el-tab-pane label="交易流水" name="transactions">
            <el-table v-loading="txLoading" :data="transactions" stripe>
              <el-table-column prop="transaction_no" label="流水号" width="200" />
              <el-table-column label="业务类型" width="140">
                <template #default="{ row }">{{ row.business_type }}</template>
              </el-table-column>
              <el-table-column label="方向" width="90">
                <template #default="{ row }">
                  <el-tag :type="row.direction === 'IN' ? 'success' : 'danger'" size="small">
                    {{ row.direction === 'IN' ? '入账' : '出账' }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="金额" width="140">
                <template #default="{ row }">
                  <span class="money" :style="{ color: row.direction === 'IN' ? '#67c23a' : '#f56c6c' }">
                    {{ row.direction === 'IN' ? '+' : '-' }}{{ formatAmount(row.amount) }}
                  </span>
                </template>
              </el-table-column>
              <el-table-column label="变动前余额" width="130">
                <template #default="{ row }"><span class="money">{{ formatAmount(row.before_balance) }}</span></template>
              </el-table-column>
              <el-table-column label="变动后余额" width="130">
                <template #default="{ row }"><span class="money">{{ formatAmount(row.after_balance) }}</span></template>
              </el-table-column>
              <el-table-column prop="reason" label="说明" min-width="140" show-overflow-tooltip />
              <el-table-column label="时间" width="170">
                <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
              </el-table-column>
            </el-table>
            <div class="pager">
              <el-pagination
                v-model:current-page="txPage"
                v-model:page-size="txPageSize"
                :total="txTotal"
                layout="total, prev, pager, next"
                @current-change="loadTransactions"
              />
            </div>
          </el-tab-pane>

          <el-tab-pane label="用户订单" name="orders">
            <el-table v-loading="orderLoading" :data="orders" stripe>
              <el-table-column prop="order_no" label="订单号" width="210" />
              <el-table-column label="类型" width="90">
                <template #default="{ row }">
                  <el-tag :type="tagType(row.order_type)" size="small">{{ statusText(row.order_type) }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="product_name" label="商品" min-width="130" show-overflow-tooltip />
              <el-table-column label="总额" width="130">
                <template #default="{ row }"><span class="money">{{ formatAmount(row.total_amount) }}</span></template>
              </el-table-column>
              <el-table-column label="状态" width="110">
                <template #default="{ row }">
                  <el-tag :type="tagType(row.status)" size="small">{{ statusText(row.status) }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column label="创建时间" width="170">
                <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
              </el-table-column>
              <el-table-column label="操作" width="90" fixed="right">
                <template #default="{ row }">
                  <el-button link type="primary" @click="router.push(`/admin/orders/${row.id}`)">详情</el-button>
                </template>
              </el-table-column>
            </el-table>
            <div class="pager">
              <el-pagination
                v-model:current-page="orderPage"
                v-model:page-size="orderPageSize"
                :total="orderTotal"
                layout="total, prev, pager, next"
                @current-change="loadOrders"
              />
            </div>
          </el-tab-pane>
        </el-tabs>
      </el-card>
    </template>

    <!-- 冻结/解冻 -->
    <el-dialog v-model="statusDialog.visible" :title="statusDialog.type === 'freeze' ? '冻结用户' : '解冻用户'" width="480px">
      <el-form ref="statusFormRef" :model="statusForm" :rules="statusRules" label-width="80px">
        <el-form-item label="原因" prop="reason">
          <el-input v-model="statusForm.reason" type="textarea" :rows="3" placeholder="请输入操作原因" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="statusDialog.visible = false">取消</el-button>
        <el-button type="primary" :loading="statusSubmitting" @click="submitStatus">确定</el-button>
      </template>
    </el-dialog>

    <!-- 余额调整 -->
    <el-dialog v-model="adjustDialog.visible" title="余额调整" width="480px">
      <el-form ref="adjustFormRef" :model="adjustForm" :rules="adjustRules" label-width="80px">
        <el-form-item label="金额" prop="amount">
          <el-input v-model="adjustForm.amount" placeholder="正数为增加，负数为扣减，如 100 或 -50" />
        </el-form-item>
        <el-form-item label="原因">
          <el-input v-model="adjustForm.reason" type="textarea" :rows="3" placeholder="可选" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="adjustDialog.visible = false">取消</el-button>
        <el-button type="primary" :loading="adjustSubmitting" @click="submitAdjust">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.page-header {
  margin-bottom: 16px;
}

.page-title-inline {
  font-size: 16px;
  font-weight: 600;
}

.card-title {
  font-weight: 600;
}

.detail-actions {
  margin-top: 16px;
}

.tab-card {
  margin-top: 16px;
}

.amount-available {
  color: #67c23a;
  font-weight: 600;
}

.amount-frozen {
  color: #f56c6c;
}
</style>
