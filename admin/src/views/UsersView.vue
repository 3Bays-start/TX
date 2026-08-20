<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import type { FormInstance, FormRules } from 'element-plus'
import { ElMessage } from 'element-plus'
import {
  adjustUserBalance,
  freezeUser,
  listUsers,
  switchLoginUser,
  unfreezeUser,
} from '@/api/admin'
import type { UserItem } from '@/api/types'
import { useAuthStore } from '@/stores/auth'
import { formatDateTime, statusText, tagType } from '@/utils/format'

const router = useRouter()
const auth = useAuthStore()

const loading = ref(false)

// ===== 用户列表 =====
const users = ref<UserItem[]>([])
const total = ref(0)
const query = reactive({
  keyword: '',
  status: '',
  riskLevel: '',
  page: 1,
  pageSize: 10,
})

function buildUserParams() {
  const params: {
    page: number
    page_size: number
    keyword?: string
    status?: string
    risk_level?: string
  } = { page: query.page, page_size: query.pageSize }
  if (query.keyword) params.keyword = query.keyword
  if (query.status) params.status = query.status
  if (query.riskLevel) params.risk_level = query.riskLevel
  return params
}

async function loadUsers() {
  loading.value = true
  try {
    const res = await listUsers(buildUserParams())
    users.value = res.items
    total.value = res.total
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  query.page = 1
  loadUsers()
}

function handleReset() {
  query.keyword = ''
  query.status = ''
  query.riskLevel = ''
  handleSearch()
}

// ===== 冻结 / 解冻 =====
const statusDialog = reactive({
  visible: false,
  type: 'freeze' as 'freeze' | 'unfreeze',
  userId: 0,
  phone: '',
})
const statusFormRef = ref<FormInstance>()
const statusForm = reactive({ reason: '' })
const statusRules: FormRules = {
  reason: [{ required: true, message: '请输入操作原因', trigger: 'blur' }],
}
const statusSubmitting = ref(false)

function openStatus(row: UserItem, type: 'freeze' | 'unfreeze') {
  statusDialog.type = type
  statusDialog.userId = row.id
  statusDialog.phone = row.phone
  statusForm.reason = ''
  statusDialog.visible = true
}

async function submitStatus() {
  if (!statusFormRef.value) return
  const valid = await statusFormRef.value.validate().catch(() => false)
  if (!valid) return
  statusSubmitting.value = true
  try {
    const reason = statusForm.reason
    if (statusDialog.type === 'freeze') {
      await freezeUser(statusDialog.userId, { reason })
    } else {
      await unfreezeUser(statusDialog.userId, { reason })
    }
    ElMessage.success(statusDialog.type === 'freeze' ? '用户已冻结' : '用户已解冻')
    statusDialog.visible = false
    loadUsers()
  } finally {
    statusSubmitting.value = false
  }
}

// ===== 余额调整 =====
const adjustDialog = reactive({ visible: false, userId: 0, phone: '' })
const adjustFormRef = ref<FormInstance>()
const adjustForm = reactive({ amount: '', reason: '' })
const adjustRules: FormRules = {
  amount: [
    { required: true, message: '请输入调整金额', trigger: 'blur' },
    {
      validator: (_rule, value: string, callback) => {
        if (value !== '' && Number.isNaN(Number(value))) callback(new Error('金额格式不正确'))
        else callback()
      },
      trigger: 'blur',
    },
  ],
}
const adjustSubmitting = ref(false)

function openAdjust(row: UserItem) {
  adjustDialog.userId = row.id
  adjustDialog.phone = row.phone
  adjustForm.amount = ''
  adjustForm.reason = ''
  adjustDialog.visible = true
}

async function submitAdjust() {
  if (!adjustFormRef.value) return
  const valid = await adjustFormRef.value.validate().catch(() => false)
  if (!valid) return
  adjustSubmitting.value = true
  try {
    await adjustUserBalance(adjustDialog.userId, {
      amount: adjustForm.amount,
      reason: adjustForm.reason,
    })
    ElMessage.success('余额调整完成')
    adjustDialog.visible = false
    loadUsers()
  } finally {
    adjustSubmitting.value = false
  }
}

function goDetail(row: UserItem) {
  router.push(`/admin/users/${row.id}`)
}

async function handleSwitchLogin(row: UserItem) {
  const res = await switchLoginUser(row.id)
  const webOrigin = window.location.origin.replace(/:\d+$/, ':5174')
  const url = `${webOrigin}/?token=${encodeURIComponent(res.access_token)}&refresh=${encodeURIComponent(res.refresh_token)}`
  window.open(url, '_blank')
  ElMessage.success(`已登录账号 ${row.phone || row.nickname}`)
}

function confirmFreeze(row: UserItem) {
  if (row.status === 'FROZEN') {
    openStatus(row, 'unfreeze')
  } else {
    openStatus(row, 'freeze')
  }
}

onMounted(loadUsers)
</script>

<template>
  <div class="page">
    <el-card shadow="never">
      <div class="filter-bar">
        <el-input
          v-model="query.keyword"
          placeholder="输入用户ID或账号/手机号"
          clearable
          style="width: 240px"
          @keyup.enter="handleSearch"
        />
        <el-select v-model="query.status" placeholder="账号状态" clearable style="width: 140px">
          <el-option label="正常" value="ACTIVE" />
          <el-option label="已冻结" value="FROZEN" />
          <el-option label="已禁用" value="DISABLED" />
        </el-select>
        <el-select v-model="query.riskLevel" placeholder="风险等级" clearable style="width: 140px">
          <el-option label="低风险" value="LOW" />
          <el-option label="中风险" value="MEDIUM" />
          <el-option label="高风险" value="HIGH" />
        </el-select>
        <el-button type="primary" @click="handleSearch">查询</el-button>
        <el-button @click="handleReset">重置</el-button>
      </div>

      <el-table v-loading="loading" :data="users" stripe>
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="phone" label="手机号" width="140" />
        <el-table-column prop="nickname" label="昵称" min-width="120" show-overflow-tooltip />
        <el-table-column label="账号状态" width="100">
          <template #default="{ row }">
            <el-tag :type="tagType(row.status)" size="small">{{ statusText(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="风险等级" width="100">
          <template #default="{ row }">
            <el-tag :type="tagType(row.risk_level)" size="small">{{ statusText(row.risk_level) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="credit_level_name" label="信用等级" width="110" />
        <el-table-column label="注册时间" width="170">
          <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="最近登录" width="170">
          <template #default="{ row }">{{ formatDateTime(row.last_login_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="290" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="goDetail(row)">详情</el-button>
            <el-button link type="success" @click="handleSwitchLogin(row)">登录该账号</el-button>
            <el-button v-if="auth.hasPerm('user:freeze')" link :type="row.status === 'FROZEN' ? 'success' : 'danger'" @click="confirmFreeze(row)">
              {{ row.status === 'FROZEN' ? '解冻' : '冻结' }}
            </el-button>
            <el-button v-if="auth.hasPerm('user:adjust')" link type="warning" @click="openAdjust(row)">调余额</el-button>
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
          @size-change="loadUsers"
          @current-change="loadUsers"
        />
      </div>
    </el-card>

    <!-- 冻结/解冻 -->
    <el-dialog
      v-model="statusDialog.visible"
      :title="statusDialog.type === 'freeze' ? '冻结用户' : '解冻用户'"
      width="480px"
    >
      <el-form ref="statusFormRef" :model="statusForm" :rules="statusRules" label-width="80px">
        <el-form-item label="用户">
          <span>ID: {{ statusDialog.userId }}（{{ statusDialog.phone }}）</span>
        </el-form-item>
        <el-form-item label="原因" prop="reason">
          <el-input v-model="statusForm.reason" type="textarea" :rows="3" placeholder="请输入操作原因" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="statusDialog.visible = false">取消</el-button>
        <el-button type="primary" :loading="statusSubmitting" @click="submitStatus">确定</el-button>
      </template>
    </el-dialog>

    <!-- 余额调整 -->
    <el-dialog v-model="adjustDialog.visible" title="余额调整" width="480px">
      <el-form ref="adjustFormRef" :model="adjustForm" :rules="adjustRules" label-width="80px">
        <el-form-item label="用户">
          <span>ID: {{ adjustDialog.userId }}（{{ adjustDialog.phone }}）</span>
        </el-form-item>
        <el-form-item label="金额" prop="amount">
          <el-input v-model="adjustForm.amount" placeholder="正数为增加，负数为扣减，如 100 或 -50" />
        </el-form-item>
        <el-form-item label="原因" prop="reason">
          <el-input v-model="adjustForm.reason" type="textarea" :rows="3" placeholder="可选" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="adjustDialog.visible = false">取消</el-button>
        <el-button type="primary" :loading="adjustSubmitting" @click="submitAdjust">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>