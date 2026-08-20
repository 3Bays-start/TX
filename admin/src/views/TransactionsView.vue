<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { listTransactions } from '@/api/admin'
import type { TransactionItem } from '@/api/types'
import { formatAmount, formatDateTime } from '@/utils/format'

const loading = ref(false)
const items = ref<TransactionItem[]>([])
const total = ref(0)
const query = reactive({
  userId: '',
  businessType: '',
  page: 1,
  pageSize: 10,
})

async function load() {
  loading.value = true
  try {
    const params: {
      page: number
      page_size: number
      user_id?: number
      business_type?: string
    } = { page: query.page, page_size: query.pageSize }
    if (query.userId) params.user_id = Number(query.userId)
    if (query.businessType) params.business_type = query.businessType
    const res = await listTransactions(params)
    items.value = res.items
    total.value = res.total
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  query.page = 1
  load()
}

function handleReset() {
  query.userId = ''
  query.businessType = ''
  handleSearch()
}

onMounted(load)
</script>

<template>
  <div class="page">
    <el-card shadow="never">
      <div class="filter-bar">
        <el-input v-model="query.userId" placeholder="用户ID" clearable style="width: 140px" @keyup.enter="handleSearch" />
        <el-select v-model="query.businessType" placeholder="业务类型" clearable style="width: 180px">
          <el-option label="订单支付" value="ORDER_PAYMENT" />
          <el-option label="撮合成交" value="MATCH_SETTLEMENT" />
          <el-option label="退款" value="REFUND" />
          <el-option label="提现" value="WITHDRAWAL" />
          <el-option label="余额调整" value="ADJUST" />
          <el-option label="会员购买" value="MEMBERSHIP_PURCHASE" />
          <el-option label="推广奖励" value="PROMOTION_REWARD" />
        </el-select>
        <el-button type="primary" @click="handleSearch">查询</el-button>
        <el-button @click="handleReset">重置</el-button>
      </div>

      <el-table v-loading="loading" :data="items" stripe>
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
        <el-table-column prop="reason" label="说明" min-width="160" show-overflow-tooltip />
        <el-table-column label="时间" width="170">
          <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
        </el-table-column>
      </el-table>

      <div class="pager">
        <el-pagination
          v-model:current-page="query.page"
          v-model:page-size="query.pageSize"
          :total="total"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next"
          @size-change="load"
          @current-change="load"
        />
      </div>
    </el-card>
  </div>
</template>
