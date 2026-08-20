<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import type { FormInstance } from 'element-plus'
import { ElMessage } from 'element-plus'
import { listRiskEvents, reviewRiskEvent } from '@/api/admin'
import type { RiskEvent } from '@/api/types'
import { useAuthStore } from '@/stores/auth'
import { formatDateTime, statusText, tagType } from '@/utils/format'

const auth = useAuthStore()
const loading = ref(false)
const items = ref<RiskEvent[]>([])
const total = ref(0)
const query = reactive({ status: '', page: 1, pageSize: 10 })

async function load() {
  loading.value = true
  try {
    const params: { page: number; page_size: number; status?: string } = {
      page: query.page,
      page_size: query.pageSize,
    }
    if (query.status) params.status = query.status
    const res = await listRiskEvents(params)
    items.value = res.items
    total.value = res.total
  } finally {
    loading.value = false
  }
}

// ===== 审核 =====
const reviewDialog = reactive({ visible: false, id: 0, eventNo: '' })
const reviewFormRef = ref<FormInstance>()
const reviewForm = reactive({ approve: true, action: 'FREEZE', reason: '' })
const reviewSubmitting = ref(false)

function openReview(row: RiskEvent) {
  reviewDialog.id = row.id
  reviewDialog.eventNo = row.event_no
  reviewForm.approve = true
  reviewForm.action = row.action || 'FREEZE'
  reviewForm.reason = ''
  reviewDialog.visible = true
}

async function submitReview() {
  reviewSubmitting.value = true
  try {
    await reviewRiskEvent(reviewDialog.id, {
      approve: reviewForm.approve,
      action: reviewForm.approve ? reviewForm.action : undefined,
      reason: reviewForm.reason,
    })
    ElMessage.success('风控事件已处理')
    reviewDialog.visible = false
    load()
  } finally {
    reviewSubmitting.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="page">
    <el-card shadow="never">
      <div class="filter-bar">
        <el-select v-model="query.status" placeholder="处理状态" clearable style="width: 160px">
          <el-option label="待处理" value="PENDING" />
          <el-option label="已处理" value="RESOLVED" />
          <el-option label="已忽略" value="DISMISSED" />
        </el-select>
        <el-button type="primary" @click="query.page = 1; load()">查询</el-button>
      </div>

      <el-table v-loading="loading" :data="items" stripe>
        <el-table-column prop="event_no" label="事件编号" width="200" />
        <el-table-column label="用户" min-width="130">
          <template #default="{ row }">
            <div style="line-height: 1.4">
              <div style="font-weight: 500">{{ row.user_nickname || row.user_username || `用户${row.user_id}` }}</div>
              <div style="font-size: 12px; color: #909399">{{ row.user_phone }}</div>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="rule_code" label="触发规则" width="130" />
        <el-table-column label="等级" width="100">
          <template #default="{ row }">
            <el-tag :type="tagType(row.level)" size="small">{{ statusText(row.level) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="action" label="处置动作" width="110" />
        <el-table-column prop="detail" label="事件详情" min-width="200" show-overflow-tooltip />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="tagType(row.status)" size="small">{{ statusText(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="创建时间" width="170">
          <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="100" fixed="right">
          <template #default="{ row }">
            <el-button v-if="auth.hasPerm('risk:review') && row.status === 'PENDING'" link type="primary" @click="openReview(row)">审核</el-button>
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

    <!-- 审核 -->
    <el-dialog v-model="reviewDialog.visible" title="风控事件审核" width="500px">
      <el-form ref="reviewFormRef" :model="reviewForm" label-width="90px">
        <el-form-item label="事件编号">
          <span>{{ reviewDialog.eventNo }}</span>
        </el-form-item>
        <el-form-item label="处理结果">
          <el-radio-group v-model="reviewForm.approve">
            <el-radio :value="true">确认处置</el-radio>
            <el-radio :value="false">忽略事件</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item v-if="reviewForm.approve" label="处置动作">
          <el-select v-model="reviewForm.action" style="width: 220px">
            <el-option label="冻结用户" value="FREEZE" />
            <el-option label="解冻用户" value="UNFREEZE" />
            <el-option label="禁用用户" value="DISABLE" />
            <el-option label="标记风险" value="MARK_RISK" />
            <el-option label="仅记录" value="LOG_ONLY" />
          </el-select>
        </el-form-item>
        <el-form-item label="处理意见">
          <el-input v-model="reviewForm.reason" type="textarea" :rows="3" placeholder="可选" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="reviewDialog.visible = false">取消</el-button>
        <el-button type="primary" :loading="reviewSubmitting" @click="submitReview">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>
