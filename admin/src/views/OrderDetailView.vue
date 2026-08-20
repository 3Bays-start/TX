<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getOrderDetail } from '@/api/admin'
import type { OrderDetail } from '@/api/types'
import { formatAmount, formatDateTime, statusText, tagType } from '@/utils/format'

const route = useRoute()
const router = useRouter()

const orderId = computed(() => Number(route.params.id))
const loading = ref(false)
const detail = ref<OrderDetail | null>(null)

async function load() {
  loading.value = true
  try {
    detail.value = await getOrderDetail(orderId.value)
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="page" v-loading="loading">
    <el-page-header class="page-header" @back="router.push('/admin/orders')">
      <template #content>
        <span class="page-title-inline">订单详情 #{{ orderId }}</span>
      </template>
    </el-page-header>

    <template v-if="detail">
      <el-row :gutter="16">
        <el-col :xs="24" :md="14">
          <el-card shadow="never">
            <template #header><span class="card-title">订单信息</span></template>
            <el-descriptions :column="2" border>
              <el-descriptions-item label="订单号">{{ detail.order_no }}</el-descriptions-item>
              <el-descriptions-item label="订单类型">
                <el-tag :type="tagType(detail.order_type)" size="small">{{ statusText(detail.order_type) }}</el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="用户">
                {{ detail.user_nickname || detail.user_username || `用户${detail.user_id}` }}（{{ detail.user_phone }}）
              </el-descriptions-item>
              <el-descriptions-item label="商品">{{ detail.product_name }}</el-descriptions-item>
              <el-descriptions-item label="订单状态">
                <el-tag :type="tagType(detail.status)" size="small">{{ statusText(detail.status) }}</el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="预约时间">{{ formatDateTime(detail.reservation_time) }}</el-descriptions-item>
              <el-descriptions-item label="创建时间">{{ formatDateTime(detail.created_at) }}</el-descriptions-item>
              <el-descriptions-item label="备注" :span="2">{{ detail.remark || '-' }}</el-descriptions-item>
            </el-descriptions>
          </el-card>
        </el-col>

        <el-col :xs="24" :md="10">
          <el-card shadow="never">
            <template #header><span class="card-title">金额明细</span></template>
            <el-descriptions :column="1" border>
              <el-descriptions-item label="订单总额">
                <span class="money">{{ formatAmount(detail.total_amount) }}</span>
              </el-descriptions-item>
              <el-descriptions-item label="服务费">
                <span class="money">{{ formatAmount(detail.service_fee) }}</span>
              </el-descriptions-item>
              <el-descriptions-item label="应付金额">
                <span class="money">{{ formatAmount(detail.payable_amount) }}</span>
              </el-descriptions-item>
              <el-descriptions-item label="已撮合金额">
                <span class="money">{{ formatAmount(detail.matched_amount) }}</span>
              </el-descriptions-item>
            </el-descriptions>
          </el-card>
        </el-col>
      </el-row>

      <el-card shadow="never" class="tab-card">
        <template #header><span class="card-title">订单凭证</span></template>
        <template v-if="detail.proof_urls?.length">
          <div class="proof-grid">
            <el-image
              v-for="(url, i) in detail.proof_urls"
              :key="i"
              :src="url"
              :preview-src-list="detail.proof_urls"
              :initial-index="i"
              fit="cover"
              class="proof-item"
              style="width: 120px; height: 120px"
            />
          </div>
          <div class="proof-meta">
            提交时间：{{ formatDateTime(detail.proof_submitted_at) }}（共 {{ detail.proof_urls.length }} 张）
          </div>
        </template>
        <el-empty v-else description="尚未上传凭证" />
      </el-card>

      <el-card shadow="never" class="tab-card">
        <template #header><span class="card-title">撮合记录</span></template>
        <el-table :data="detail.matches" stripe empty-text="暂无撮合记录">
          <el-table-column prop="match_no" label="撮合编号" min-width="160" />
          <el-table-column prop="buyer_order_id" label="买方订单ID" width="120" />
          <el-table-column prop="seller_order_id" label="卖方订单ID" width="120" />
          <el-table-column label="卖方用户" min-width="130">
            <template #default="{ row }">
              <div style="line-height: 1.4">
                <div style="font-weight: 500">{{ row.seller_nickname || `用户${row.seller_user_id}` }}</div>
                <div style="font-size: 12px; color: #909399">{{ row.seller_phone }}</div>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="撮合金额" width="140">
            <template #default="{ row }"><span class="money">{{ formatAmount(row.match_amount) }}</span></template>
          </el-table-column>
          <el-table-column label="状态" width="110">
            <template #default="{ row }">
              <el-tag :type="tagType(row.status)" size="small">{{ statusText(row.status) }}</el-tag>
            </template>
          </el-table-column>
        </el-table>
      </el-card>

      <el-card shadow="never" class="tab-card">
        <template #header><span class="card-title">状态流转记录</span></template>
        <el-table :data="detail.status_logs" stripe empty-text="暂无状态记录">
          <el-table-column label="原状态" width="160">
            <template #default="{ row }">{{ statusText(row.from_status) || '-' }}</template>
          </el-table-column>
          <el-table-column label="新状态" width="160">
            <template #default="{ row }">{{ statusText(row.to_status) || '-' }}</template>
          </el-table-column>
          <el-table-column prop="reason" label="原因" min-width="180" show-overflow-tooltip />
          <el-table-column label="时间" width="170">
            <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
          </el-table-column>
        </el-table>
      </el-card>
    </template>
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

.tab-card {
  margin-top: 16px;
}

.proof-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.proof-meta {
  margin-top: 12px;
  color: #909399;
  font-size: 13px;
}
</style>
