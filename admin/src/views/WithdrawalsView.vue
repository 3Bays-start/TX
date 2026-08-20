<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import type { FormInstance, FormRules } from 'element-plus'
import { ElMessage, ElMessageBox } from 'element-plus'
import { completeWithdrawal, listWithdrawals, reviewWithdrawal } from '@/api/admin'
import type { WithdrawalItem } from '@/api/types'
import { useAuthStore } from '@/stores/auth'
import { formatAmount, formatDateTime, statusText, tagType } from '@/utils/format'

const auth = useAuthStore()
const loading = ref(false)
const items = ref<WithdrawalItem[]>([])
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
    const res = await listWithdrawals(params)
    items.value = res.items
    total.value = res.total
  } finally {
    loading.value = false
  }
}

// ===== 审核 =====
const reviewDialog = reactive({ visible: false, id: 0, withdrawalNo: '' })
const reviewFormRef = ref<FormInstance>()
const reviewForm = reactive({ approve: true, reason: '' })
const reviewRules: FormRules = {
  reason: [{ required: true, message: '请输入审核意见', trigger: 'blur' }],
}
const reviewSubmitting = ref(false)

function openReview(row: WithdrawalItem) {
  reviewDialog.id = row.id
  reviewDialog.withdrawalNo = row.withdrawal_no
  reviewForm.approve = true
  reviewForm.reason = ''
  reviewDialog.visible = true
}

async function submitReview() {
  if (!reviewFormRef.value) return
  const valid = await reviewFormRef.value.validate().catch(() => false)
  if (!valid) return
  reviewSubmitting.value = true
  try {
    await reviewWithdrawal(reviewDialog.id, {
      approve: reviewForm.approve,
      reason: reviewForm.reason,
    })
    ElMessage.success('提现审核完成')
    reviewDialog.visible = false
    load()
  } finally {
    reviewSubmitting.value = false
  }
}

// ===== 完成 =====
function handleComplete(row: WithdrawalItem) {
  ElMessageBox.confirm(`确认标记提现单 ${row.withdrawal_no} 为已完成？`, '提示', { type: 'warning' })
    .then(async () => {
      await completeWithdrawal(row.id)
      ElMessage.success('提现已完成')
      load()
    })
    .catch(() => {})
}

onMounted(load)
</script>

<template>
  <div class="page">
    <el-card shadow="never">
      <div class="filter-bar">
        <el-select v-model="query.status" placeholder="提现状态" clearable style="width: 160px">
          <el-option label="待审核" value="PENDING" />
          <el-option label="审核中" value="REVIEWING" />
          <el-option label="已通过" value="APPROVED" />
          <el-option label="已拒绝" value="REJECTED" />
          <el-option label="已完成" value="COMPLETED" />
          <el-option label="已取消" value="CANCELLED" />
        </el-select>
        <el-button type="primary" @click="query.page = 1; load()">查询</el-button>
      </div>

      <el-table v-loading="loading" :data="items" stripe>
        <el-table-column prop="withdrawal_no" label="提现单号" width="200" />
        <el-table-column label="用户" min-width="130">
          <template #default="{ row }">
            <div style="line-height: 1.4">
              <div style="font-weight: 500">{{ row.user_nickname || row.user_username || `用户${row.user_id}` }}</div>
              <div style="font-size: 12px; color: #909399">{{ row.user_phone }}</div>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="申请金额" width="130">
          <template #default="{ row }"><span class="money">{{ formatAmount(row.amount) }}</span></template>
        </el-table-column>
        <el-table-column label="实发金额" width="130">
          <template #default="{ row }"><span class="money">{{ formatAmount(row.actual_amount) }}</span></template>
        </el-table-column>
        <el-table-column prop="usdt_address" label="USDT 地址" min-width="200" show-overflow-tooltip />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="tagType(row.status)" size="small">{{ statusText(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="review_reason" label="审核意见" min-width="120" show-overflow-tooltip />
        <el-table-column label="申请时间" width="170">
          <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <template v-if="auth.hasPerm('withdrawal:review')">
              <el-button v-if="['PENDING', 'REVIEWING'].includes(row.status)" link type="primary" @click="openReview(row)">审核</el-button>
              <el-button v-if="row.status === 'APPROVED'" link type="success" @click="handleComplete(row)">完成</el-button>
            </template>
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
    <el-dialog v-model="reviewDialog.visible" title="提现审核" width="480px">
      <el-form ref="reviewFormRef" :model="reviewForm" :rules="reviewRules" label-width="90px">
        <el-form-item label="提现单号">
          <span>{{ reviewDialog.withdrawalNo }}</span>
        </el-form-item>
        <el-form-item label="审核结果">
          <el-radio-group v-model="reviewForm.approve">
            <el-radio :value="true">通过</el-radio>
            <el-radio :value="false">拒绝</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="审核意见" prop="reason">
          <el-input v-model="reviewForm.reason" type="textarea" :rows="3" placeholder="请输入审核意见" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="reviewDialog.visible = false">取消</el-button>
        <el-button type="primary" :loading="reviewSubmitting" @click="submitReview">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>
