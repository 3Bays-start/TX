<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { listPromotions } from '@/api/admin'
import type { PromotionItem } from '@/api/types'
import { formatAmount, formatDateTime, statusText, tagType } from '@/utils/format'

const loading = ref(false)
const items = ref<PromotionItem[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(10)

async function load() {
  loading.value = true
  try {
    const res = await listPromotions({ page: page.value, page_size: pageSize.value })
    items.value = res.items
    total.value = res.total
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="page">
    <el-card shadow="never">
      <el-table v-loading="loading" :data="items" stripe>
        <el-table-column prop="record_no" label="奖励编号" width="200" />
        <el-table-column label="来源用户" min-width="130">
          <template #default="{ row }">
            <div style="line-height: 1.4">
              <div style="font-weight: 500">{{ row.source_user_nickname || row.source_user_username || `用户${row.source_user_id}` }}</div>
              <div style="font-size: 12px; color: #909399">{{ row.source_user_phone }}</div>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="source_order_id" label="来源订单ID" width="120" />
        <el-table-column label="受益用户" min-width="130">
          <template #default="{ row }">
            <div style="line-height: 1.4">
              <div style="font-weight: 500">{{ row.beneficiary_user_nickname || row.beneficiary_user_username || `用户${row.beneficiary_user_id}` }}</div>
              <div style="font-size: 12px; color: #909399">{{ row.beneficiary_user_phone }}</div>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="奖励金额" width="140">
          <template #default="{ row }"><span class="money" style="color: #67c23a">{{ formatAmount(row.reward_amount) }}</span></template>
        </el-table-column>
        <el-table-column label="状态" width="110">
          <template #default="{ row }">
            <el-tag :type="tagType(row.status)" size="small">{{ statusText(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="创建时间" width="170">
          <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
        </el-table-column>
      </el-table>

      <div class="pager">
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
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
