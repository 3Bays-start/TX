<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { listLogs } from '@/api/admin'
import type { OperationLog } from '@/api/types'
import { formatDateTime } from '@/utils/format'

const loading = ref(false)
const items = ref<OperationLog[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(10)

async function load() {
  loading.value = true
  try {
    const res = await listLogs({ page: page.value, page_size: pageSize.value })
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
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="operator_type" label="操作者类型" width="110" />
        <el-table-column prop="operator_id" label="操作者ID" width="100" />
        <el-table-column prop="module" label="模块" width="100" />
        <el-table-column prop="action" label="动作" width="150" />
        <el-table-column prop="target_type" label="目标类型" width="130" />
        <el-table-column prop="target_id" label="目标ID" width="100" />
        <el-table-column prop="reason" label="原因" min-width="140" show-overflow-tooltip />
        <el-table-column prop="ip" label="IP" width="130" />
        <el-table-column prop="request_id" label="请求ID" width="150" show-overflow-tooltip />
        <el-table-column label="时间" width="170" fixed="right">
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
