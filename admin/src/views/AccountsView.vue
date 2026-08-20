<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getUserAccount, listTransactions, listUsers } from '@/api/admin'
import type { AccountInfo, TransactionItem, UserItem } from '@/api/types'
import { formatAmount, formatDateTime } from '@/utils/format'

const router = useRouter()

const loading = ref(false)
const userId = ref<number | undefined>()
const account = ref<AccountInfo | null>(null)
const searched = ref(false)
const userOptions = ref<UserItem[]>([])

const transactions = ref<TransactionItem[]>([])
const txTotal = ref(0)
const txPage = ref(1)
const txPageSize = ref(10)
const txLoading = ref(false)

const query = reactive({ businessType: '' })

async function loadUserOptions() {
  const res = await listUsers({ page: 1, page_size: 500 })
  userOptions.value = res.items
}

async function search() {
  if (!userId.value) {
    ElMessage.warning('请选择账户')
    return
  }
  loading.value = true
  try {
    account.value = await getUserAccount(userId.value)
    searched.value = true
    txPage.value = 1
    await loadTransactions()
  } finally {
    loading.value = false
  }
}

async function loadTransactions() {
  if (!userId.value) return
  txLoading.value = true
  try {
    const params: { user_id: number; page: number; page_size: number; business_type?: string } = {
      user_id: userId.value,
      page: txPage.value,
      page_size: txPageSize.value,
    }
    if (query.businessType) params.business_type = query.businessType
    const res = await listTransactions(params)
    transactions.value = res.items
    txTotal.value = res.total
  } finally {
    txLoading.value = false
  }
}

function goDetail() {
  if (userId.value) router.push(`/admin/users/${userId.value}`)
}

onMounted(loadUserOptions)
</script>

<template>
  <div class="page">
    <el-card shadow="never">
      <div class="filter-bar">
        <el-select
          v-model="userId"
          filterable
          clearable
          placeholder="选择账户（手机号/昵称）"
          style="width: 280px"
          @change="search"
        >
          <el-option
            v-for="u in userOptions"
            :key="u.id"
            :value="u.id"
            :label="`${u.phone}（${u.nickname}）`"
          >
            <div style="line-height: 1.4">
              <div style="font-weight: 500">{{ u.nickname }}</div>
              <div style="font-size: 12px; color: #909399">{{ u.phone }}（ID: {{ u.id }}）</div>
            </div>
          </el-option>
        </el-select>
        <el-button type="primary" :loading="loading" @click="search">查询</el-button>
        <el-button :disabled="!userId" @click="goDetail">查看详情</el-button>
      </div>

      <template v-if="account && searched">
        <el-descriptions :column="4" border class="account-info">
          <el-descriptions-item label="账户号">{{ account.account_no }}</el-descriptions-item>
          <el-descriptions-item label="可用余额">
            <span class="money" style="color: #67c23a; font-weight: 600">{{ formatAmount(account.available_amount) }}</span>
          </el-descriptions-item>
          <el-descriptions-item label="冻结余额">
            <span class="money" style="color: #f56c6c">{{ formatAmount(account.frozen_amount) }}</span>
          </el-descriptions-item>
          <el-descriptions-item label="待结算金额">
            <span class="money">{{ formatAmount(account.pending_amount) }}</span>
          </el-descriptions-item>
        </el-descriptions>
      </template>
    </el-card>

    <el-card shadow="never" class="tx-card">
      <template #header>
        <div class="tx-header">
          <span class="card-title">交易流水</span>
          <el-select v-model="query.businessType" placeholder="业务类型" clearable style="width: 180px" @change="loadTransactions">
            <el-option label="订单支付" value="ORDER_PAYMENT" />
            <el-option label="撮合成交" value="MATCH_SETTLEMENT" />
            <el-option label="退款" value="REFUND" />
            <el-option label="提现" value="WITHDRAWAL" />
            <el-option label="余额调整" value="ADJUST" />
            <el-option label="会员购买" value="MEMBERSHIP_PURCHASE" />
            <el-option label="推广奖励" value="PROMOTION_REWARD" />
          </el-select>
        </div>
      </template>
      <el-table v-loading="txLoading" :data="transactions" stripe>
        <el-table-column prop="transaction_no" label="流水号" width="200" />
        <el-table-column label="用户" min-width="130">
          <template #default="{ row }">
            <div style="line-height: 1.4">
              <div style="font-weight: 500">{{ row.user_nickname || row.user_username || `用户${row.user_id}` }}</div>
              <div style="font-size: 12px; color: #909399">{{ row.user_phone }}</div>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="business_type" label="业务类型" width="150" />
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
        <el-table-column label="变动前" width="120">
          <template #default="{ row }"><span class="money">{{ formatAmount(row.before_balance) }}</span></template>
        </el-table-column>
        <el-table-column label="变动后" width="120">
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
    </el-card>
  </div>
</template>

<style scoped>
.account-info {
  margin-top: 8px;
}

.tx-card {
  margin-top: 16px;
}

.tx-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.card-title {
  font-weight: 600;
}
</style>
