<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import type { FormInstance, FormRules } from 'element-plus'
import { ElMessage } from 'element-plus'
import { listAppeals, processAppeal } from '@/api/admin'
import type { Appeal } from '@/api/types'
import { useAuthStore } from '@/stores/auth'
import { formatDateTime, statusText, tagType } from '@/utils/format'

const auth = useAuthStore()
const loading = ref(false)
const items = ref<Appeal[]>([])
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
    const res = await listAppeals(params)
    items.value = res.items
    total.value = res.total
  } finally {
    loading.value = false
  }
}

// ===== 处理 =====
const processDialog = reactive({ visible: false, id: 0, appealNo: '' })
const processFormRef = ref<FormInstance>()
const processForm = reactive({ approve: true, result: '' })
const processRules: FormRules = {
  result: [{ required: true, message: '请输入处理结果说明', trigger: 'blur' }],
}
const processSubmitting = ref(false)

function openProcess(row: Appeal) {
  processDialog.id = row.id
  processDialog.appealNo = row.appeal_no
  processForm.approve = true
  processForm.result = ''
  processDialog.visible = true
}

async function submitProcess() {
  if (!processFormRef.value) return
  const valid = await processFormRef.value.validate().catch(() => false)
  if (!valid) return
  processSubmitting.value = true
  try {
    await processAppeal(processDialog.id, {
      approve: processForm.approve,
      result: processForm.result,
    })
    ElMessage.success('申诉已处理')
    processDialog.visible = false
    load()
  } finally {
    processSubmitting.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="page">
    <el-card shadow="never">
      <div class="filter-bar">
        <el-select v-model="query.status" placeholder="申诉状态" clearable style="width: 160px">
          <el-option label="待处理" value="PENDING" />
          <el-option label="处理中" value="PROCESSING" />
          <el-option label="已通过" value="APPROVED" />
          <el-option label="已驳回" value="REJECTED" />
          <el-option label="已关闭" value="CLOSED" />
        </el-select>
        <el-button type="primary" @click="query.page = 1; load()">查询</el-button>
      </div>

      <el-table v-loading="loading" :data="items" stripe>
        <el-table-column prop="appeal_no" label="申诉编号" width="200" />
        <el-table-column label="用户" min-width="130">
          <template #default="{ row }">
            <div style="line-height: 1.4">
              <div style="font-weight: 500">{{ row.user_nickname || row.user_username || `用户${row.user_id}` }}</div>
              <div style="font-size: 12px; color: #909399">{{ row.user_phone }}</div>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="order_id" label="订单ID" width="90" />
        <el-table-column prop="subject" label="申诉主题" min-width="200" show-overflow-tooltip />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="tagType(row.status)" size="small">{{ statusText(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="result" label="处理结果" min-width="140" show-overflow-tooltip />
        <el-table-column label="创建时间" width="170">
          <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="100" fixed="right">
          <template #default="{ row }">
            <el-button v-if="auth.hasPerm('appeal:process') && ['PENDING', 'PROCESSING'].includes(row.status)" link type="primary" @click="openProcess(row)">处理</el-button>
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

    <!-- 处理 -->
    <el-dialog v-model="processDialog.visible" title="处理申诉" width="500px">
      <el-form ref="processFormRef" :model="processForm" :rules="processRules" label-width="90px">
        <el-form-item label="申诉编号">
          <span>{{ processDialog.appealNo }}</span>
        </el-form-item>
        <el-form-item label="处理结果">
          <el-radio-group v-model="processForm.approve">
            <el-radio :value="true">申诉成立</el-radio>
            <el-radio :value="false">驳回申诉</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="结果说明" prop="result">
          <el-input v-model="processForm.result" type="textarea" :rows="3" placeholder="请输入处理结果说明" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="processDialog.visible = false">取消</el-button>
        <el-button type="primary" :loading="processSubmitting" @click="submitProcess">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>
