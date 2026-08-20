<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { listOrders } from '@/api/admin'
import type { OrderItem } from '@/api/types'
import { formatAmount, formatDateTime, statusText, tagType } from '@/utils/format'

const router = useRouter()
const loading = ref(false)
const orders = ref<OrderItem[]>([])
const total = ref(0)
const query = reactive({
  orderNo: '',
  status: '',
  orderType: '',
  userId: '',
  page: 1,
  pageSize: 10,
})

async function load() {
  loading.value = true
  try {
    const params: {
      page: number
      page_size: number
      order_no?: string
      status?: string
      order_type?: string
      user_id?: number
    } = { page: query.page, page_size: query.pageSize }
    if (query.orderNo) params.order_no = query.orderNo
    if (query.status) params.status = query.status
    if (query.orderType) params.order_type = query.orderType
    if (query.userId) params.user_id = Number(query.userId)
    const res = await listOrders(params)
    orders.value = res.items
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
  query.orderNo = ''
  query.status = ''
  query.orderType = ''
  query.userId = ''
  handleSearch()
}

onMounted(load)
</script>

<template>
  <div class="page">
    <el-card shadow="never">
      <div class="filter-bar">
        <el-input v-model="query.orderNo" placeholder="订单号" clearable style="width: 220px" @keyup.enter="handleSearch" />
        <el-input v-model="query.userId" placeholder="用户ID" clearable style="width: 120px" @keyup.enter="handleSearch" />
        <el-select v-model="query.orderType" placeholder="订单类型" clearable style="width: 130px">
          <el-option label="买入" value="BUY" />
          <el-option label="卖出" value="SELL" />
        </el-select>
        <el-select v-model="query.status" placeholder="订单状态" clearable style="width: 150px">
          <el-option label="已创建" value="CREATED" />
          <el-option label="待支付" value="WAITING_PAYMENT" />
          <el-option label="已支付" value="PAID" />
          <el-option label="待撮合" value="WAITING_MATCH" />
          <el-option label="部分撮合" value="PARTIAL_MATCHED" />
          <el-option label="已撮合" value="FULL_MATCHED" />
          <el-option label="服务中" value="PROCESSING" />
          <el-option label="已完成" value="COMPLETED" />
          <el-option label="争议中" value="DISPUTED" />
          <el-option label="风控复核" value="RISK_REVIEW" />
          <el-option label="已过期" value="EXPIRED" />
          <el-option label="已取消" value="CANCELLED" />
        </el-select>
        <el-button type="primary" @click="handleSearch">查询</el-button>
        <el-button @click="handleReset">重置</el-button>
      </div>

      <el-table v-loading="loading" :data="orders" stripe>
        <el-table-column prop="order_no" label="订单号" width="210" />
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column label="用户" min-width="130">
          <template #default="{ row }">
            <div style="line-height: 1.4">
              <div style="font-weight: 500">{{ row.user_nickname || row.user_username || `用户${row.user_id}` }}</div>
              <div style="font-size: 12px; color: #909399">{{ row.user_phone }}</div>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="类型" width="90">
          <template #default="{ row }">
            <el-tag :type="tagType(row.order_type)" size="small">{{ statusText(row.order_type) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="product_name" label="商品" min-width="140" show-overflow-tooltip />
        <el-table-column label="总额" width="130">
          <template #default="{ row }"><span class="money">{{ formatAmount(row.total_amount) }}</span></template>
        </el-table-column>
        <el-table-column label="服务费" width="120">
          <template #default="{ row }"><span class="money">{{ formatAmount(row.service_fee) }}</span></template>
        </el-table-column>
        <el-table-column label="已撮合" width="120">
          <template #default="{ row }"><span class="money">{{ formatAmount(row.matched_amount) }}</span></template>
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
