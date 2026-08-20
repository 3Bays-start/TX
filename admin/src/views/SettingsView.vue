<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import type { FormInstance } from 'element-plus'
import { ElMessage } from 'element-plus'
import { createSystemInvites, listFeeRules, updateFeeRule } from '@/api/admin'
import type { FeeRule, InviteCode } from '@/api/types'
import { formatAmount, formatDateTime, statusText, tagType } from '@/utils/format'

// ===== 费率设置 =====
const feeLoading = ref(false)
const feeRules = ref<FeeRule[]>([])

const feeDialog = reactive({ visible: false })
const feeFormRef = ref<FormInstance>()
const feeForm = reactive({
  feeType: '',
  name: '',
  rate: '',
  minFee: '',
  maxFee: '',
  status: 'ACTIVE',
})
const feeSubmitting = ref(false)

async function loadFees() {
  feeLoading.value = true
  try {
    const res = await listFeeRules()
    feeRules.value = res.items
  } finally {
    feeLoading.value = false
  }
}

function openFeeEdit(row: FeeRule) {
  feeForm.feeType = row.fee_type
  feeForm.name = row.name
  feeForm.rate = row.rate
  feeForm.minFee = row.min_fee
  feeForm.maxFee = row.max_fee
  feeForm.status = row.status
  feeDialog.visible = true
}

async function submitFee() {
  feeSubmitting.value = true
  try {
    await updateFeeRule(feeForm.feeType, {
      name: feeForm.name,
      rate: feeForm.rate,
      min_fee: feeForm.minFee,
      max_fee: feeForm.maxFee,
      status: feeForm.status,
    })
    ElMessage.success('费率已更新')
    feeDialog.visible = false
    loadFees()
  } finally {
    feeSubmitting.value = false
  }
}

// ===== 邀请码生成 =====
const inviteLoading = ref(false)
const inviteFormRef = ref<FormInstance>()
const inviteForm = reactive({ count: 10, expiresInDays: 30 })
const inviteRules = {
  count: [{ required: true, message: '请输入生成数量', trigger: 'blur' }],
}
const inviteSubmitting = ref(false)
const inviteCodes = ref<InviteCode[]>([])

async function submitInvites() {
  inviteSubmitting.value = true
  try {
    const res = await createSystemInvites({
      count: inviteForm.count,
      expires_in_days: inviteForm.expiresInDays,
    })
    inviteCodes.value = res.items
    ElMessage.success(`已生成 ${res.items.length} 个邀请码`)
  } finally {
    inviteSubmitting.value = false
  }
}

onMounted(loadFees)
</script>

<template>
  <div class="page">
    <el-row :gutter="16">
      <el-col :xs="24" :lg="14">
        <el-card shadow="never">
          <template #header><span class="card-title">服务费规则设置</span></template>
          <el-table v-loading="feeLoading" :data="feeRules" stripe>
            <el-table-column prop="fee_type" label="费率类型" width="170" />
            <el-table-column prop="name" label="名称" width="140" />
            <el-table-column label="费率" width="100">
              <template #default="{ row }">{{ row.rate }}%</template>
            </el-table-column>
            <el-table-column label="最低" width="100">
              <template #default="{ row }"><span class="money">{{ formatAmount(row.min_fee) }}</span></template>
            </el-table-column>
            <el-table-column label="最高" width="100">
              <template #default="{ row }"><span class="money">{{ formatAmount(row.max_fee) }}</span></template>
            </el-table-column>
            <el-table-column label="状态" width="90">
              <template #default="{ row }">
                <el-tag :type="tagType(row.status)" size="small">{{ statusText(row.status) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="80" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" @click="openFeeEdit(row)">编辑</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>

      <el-col :xs="24" :lg="10">
        <el-card shadow="never">
          <template #header><span class="card-title">系统邀请码生成</span></template>
          <el-form ref="inviteFormRef" :model="inviteForm" :rules="inviteRules" label-width="90px">
            <el-form-item label="生成数量" prop="count">
              <el-input-number v-model="inviteForm.count" :min="1" :max="1000" />
            </el-form-item>
            <el-form-item label="有效期(天)">
              <el-input-number v-model="inviteForm.expiresInDays" :min="0" :max="3650" />
              <div class="muted" style="margin-left: 8px">0 表示永久有效</div>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="inviteSubmitting" @click="submitInvites">
                生成邀请码
              </el-button>
            </el-form-item>
          </el-form>

          <el-divider v-if="inviteCodes.length" content-position="left">生成结果</el-divider>
          <div v-if="inviteCodes.length" class="invite-result">
            <el-tag
              v-for="code in inviteCodes"
              :key="code.id"
              class="invite-code"
              size="large"
              effect="plain"
            >
              {{ code.code }}
            </el-tag>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 编辑费率 -->
    <el-dialog v-model="feeDialog.visible" title="编辑费率" width="480px">
      <el-form ref="feeFormRef" :model="feeForm" label-width="90px">
        <el-form-item label="费率类型">
          <el-input v-model="feeForm.feeType" disabled />
        </el-form-item>
        <el-form-item label="名称">
          <el-input v-model="feeForm.name" />
        </el-form-item>
        <el-form-item label="费率(%)">
          <el-input v-model="feeForm.rate" />
        </el-form-item>
        <el-form-item label="最低费用">
          <el-input v-model="feeForm.minFee" />
        </el-form-item>
        <el-form-item label="最高费用">
          <el-input v-model="feeForm.maxFee" />
        </el-form-item>
        <el-form-item label="状态">
          <el-radio-group v-model="feeForm.status">
            <el-radio value="ACTIVE">启用</el-radio>
            <el-radio value="INACTIVE">停用</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="feeDialog.visible = false">取消</el-button>
        <el-button type="primary" :loading="feeSubmitting" @click="submitFee">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.card-title {
  font-weight: 600;
}

.invite-result {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  max-height: 260px;
  overflow-y: auto;
}
</style>
