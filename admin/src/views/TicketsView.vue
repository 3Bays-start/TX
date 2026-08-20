<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import type { FormInstance, FormRules } from 'element-plus'
import { ElMessage, ElMessageBox } from 'element-plus'
import { closeTicket, listTickets, replyTicket } from '@/api/admin'
import type { Ticket } from '@/api/types'
import { useAuthStore } from '@/stores/auth'
import { formatDateTime, statusText, tagType } from '@/utils/format'

const auth = useAuthStore()
const loading = ref(false)
const items = ref<Ticket[]>([])
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
    const res = await listTickets(params)
    items.value = res.items
    total.value = res.total
  } finally {
    loading.value = false
  }
}

// ===== 回复 =====
const replyDialog = reactive({ visible: false, id: 0, ticketNo: '' })
const replyFormRef = ref<FormInstance>()
const replyForm = reactive({ content: '', attachments: '' })
const replyRules: FormRules = {
  content: [{ required: true, message: '请输入回复内容', trigger: 'blur' }],
}
const replySubmitting = ref(false)

function openReply(row: Ticket) {
  replyDialog.id = row.id
  replyDialog.ticketNo = row.ticket_no
  replyForm.content = ''
  replyForm.attachments = ''
  replyDialog.visible = true
}

async function submitReply() {
  if (!replyFormRef.value) return
  const valid = await replyFormRef.value.validate().catch(() => false)
  if (!valid) return
  replySubmitting.value = true
  try {
    await replyTicket(replyDialog.id, {
      content: replyForm.content,
      attachments: replyForm.attachments || undefined,
    })
    ElMessage.success('回复成功')
    replyDialog.visible = false
    load()
  } finally {
    replySubmitting.value = false
  }
}

// ===== 关闭 =====
function handleClose(row: Ticket) {
  ElMessageBox.confirm(`确认关闭工单 ${row.ticket_no}？`, '提示', { type: 'warning' })
    .then(async () => {
      await closeTicket(row.id)
      ElMessage.success('工单已关闭')
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
        <el-select v-model="query.status" placeholder="工单状态" clearable style="width: 160px">
          <el-option label="待处理" value="PENDING" />
          <el-option label="处理中" value="PROCESSING" />
          <el-option label="已关闭" value="CLOSED" />
        </el-select>
        <el-button type="primary" @click="query.page = 1; load()">查询</el-button>
      </div>

      <el-table v-loading="loading" :data="items" stripe>
        <el-table-column prop="ticket_no" label="工单号" width="200" />
        <el-table-column label="用户" min-width="130">
          <template #default="{ row }">
            <div style="line-height: 1.4">
              <div style="font-weight: 500">{{ row.user_nickname || row.user_username || `用户${row.user_id}` }}</div>
              <div style="font-size: 12px; color: #909399">{{ row.user_phone }}</div>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="category" label="分类" width="120" />
        <el-table-column prop="title" label="标题" min-width="200" show-overflow-tooltip />
        <el-table-column label="优先级" width="100">
          <template #default="{ row }">
            <el-tag :type="tagType(row.priority)" size="small">{{ statusText(row.priority) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="tagType(row.status)" size="small">{{ statusText(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="创建时间" width="170">
          <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="130" fixed="right">
          <template #default="{ row }">
            <el-button v-if="auth.hasPerm('ticket:reply') && row.status !== 'CLOSED'" link type="primary" @click="openReply(row)">回复</el-button>
            <el-button v-if="auth.hasPerm('ticket:close') && row.status !== 'CLOSED'" link type="danger" @click="handleClose(row)">关闭</el-button>
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

    <!-- 回复 -->
    <el-dialog v-model="replyDialog.visible" title="回复工单" width="520px">
      <el-form ref="replyFormRef" :model="replyForm" :rules="replyRules" label-width="80px">
        <el-form-item label="工单号">
          <span>{{ replyDialog.ticketNo }}</span>
        </el-form-item>
        <el-form-item label="回复内容" prop="content">
          <el-input v-model="replyForm.content" type="textarea" :rows="5" placeholder="请输入回复内容" />
        </el-form-item>
        <el-form-item label="附件">
          <el-input v-model="replyForm.attachments" placeholder="附件链接，多个用逗号分隔（可选）" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="replyDialog.visible = false">取消</el-button>
        <el-button type="primary" :loading="replySubmitting" @click="submitReply">发送回复</el-button>
      </template>
    </el-dialog>
  </div>
</template>
