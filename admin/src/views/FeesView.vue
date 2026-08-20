<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import type { FormInstance } from 'element-plus'
import { ElMessage } from 'element-plus'
import { listFeeRecords, listFeeRules, updateFeeRule } from '@/api/admin'
import type { FeeRecord, FeeRule } from '@/api/types'
import { useAuthStore } from '@/stores/auth'
import { formatAmount, formatDateTime, statusText, tagType } from '@/utils/format'

const auth = useAuthStore()
const activeTab = ref('rules')
const loading = ref(false)
const rules = ref<FeeRule[]>([])

// ===== 费率记录 =====
const records = ref<FeeRecord[]>([])
const recordTotal = ref(0)
const recordPage = ref(1)
const recordPageSize = ref(10)

// ===== 编辑费率 =====
const editDialog = reactive({ visible: false })
const editFormRef = ref<FormInstance>()
const editForm = reactive({
  feeType: '',
  name: '',
  rate: '',
  minFee: '',
  maxFee: '',
  status: 'ACTIVE',
})
const editSubmitting = ref(false)

async function loadRules() {
  loading.value = true
  try {
    const res = await listFeeRules()
    rules.value = res.items
  } finally {
    loading.value = false
  }
}

async function loadRecords() {
  loading.value = true
  try {
    const res = await listFeeRecords({ page: recordPage.value, page_size: recordPageSize.value })
    records.value = res.items
    recordTotal.value = res.total
  } finally {
    loading.value = false
  }
}

function handleTabChange() {
  if (activeTab.value === 'records') loadRecords()
  else loadRules()
}

function openEdit(row: FeeRule) {
  editForm.feeType = row.fee_type
  editForm.name = row.name
  editForm.rate = row.rate
  editForm.minFee = row.min_fee
  editForm.maxFee = row.max_fee
  editForm.status = row.status
  editDialog.visible = true
}

async function submitEdit() {
  editSubmitting.value = true
  try {
    await updateFeeRule(editForm.feeType, {
      name: editForm.name,
      rate: editForm.rate,
      min_fee: editForm.minFee,
      max_fee: editForm.maxFee,
      status: editForm.status,
    })
    ElMessage.success('费率已更新')
    editDialog.visible = false
    loadRules()
  } finally {
    editSubmitting.value = false
  }
}

onMounted(loadRules)
</script>

<template>
  <div class="page">
    <el-card shadow="never">
      <el-tabs v-model="activeTab" @tab-change="handleTabChange">
        <el-tab-pane label="费率规则" name="rules">
          <el-table v-loading="loading" :data="rules" stripe>
            <el-table-column prop="fee_type" label="费率类型" width="200" />
            <el-table-column prop="name" label="名称" width="160" />
            <el-table-column label="费率" width="120">
              <template #default="{ row }">{{ row.rate }}%</template>
            </el-table-column>
            <el-table-column label="最低费用" width="140">
              <template #default="{ row }"><span class="money">{{ formatAmount(row.min_fee) }}</span></template>
            </el-table-column>
            <el-table-column label="最高费用" width="140">
              <template #default="{ row }"><span class="money">{{ formatAmount(row.max_fee) }}</span></template>
            </el-table-column>
            <el-table-column label="状态" width="100">
              <template #default="{ row }">
                <el-tag :type="tagType(row.status)" size="small">{{ statusText(row.status) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="生效时间" width="180">
              <template #default="{ row }">{{ formatDateTime(row.effective_at) }}</template>
            </el-table-column>
            <el-table-column label="操作" width="100" fixed="right">
              <template #default="{ row }">
                <el-button v-if="auth.hasPerm('fee:edit')" link type="primary" @click="openEdit(row)">编辑</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <el-tab-pane label="费率记录" name="records">
          <el-table v-loading="loading" :data="records" stripe>
            <el-table-column prop="fee_no" label="费用编号" width="200" />
            <el-table-column prop="order_id" label="订单ID" width="100" />
            <el-table-column prop="fee_type" label="费率类型" width="180" />
            <el-table-column label="计费基数" width="140">
              <template #default="{ row }"><span class="money">{{ formatAmount(row.base_amount) }}</span></template>
            </el-table-column>
            <el-table-column label="费率" width="110">
              <template #default="{ row }">{{ row.rate }}%</template>
            </el-table-column>
            <el-table-column label="费用金额" width="140">
              <template #default="{ row }"><span class="money" style="color: #f56c6c">{{ formatAmount(row.fee_amount) }}</span></template>
            </el-table-column>
            <el-table-column label="时间" width="170">
              <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
            </el-table-column>
          </el-table>
          <div class="pager">
            <el-pagination
              v-model:current-page="recordPage"
              v-model:page-size="recordPageSize"
              :total="recordTotal"
              layout="total, prev, pager, next"
              @current-change="loadRecords"
            />
          </div>
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <!-- 编辑费率 -->
    <el-dialog v-model="editDialog.visible" title="编辑费率" width="480px">
      <el-form ref="editFormRef" :model="editForm" label-width="90px">
        <el-form-item label="费率类型">
          <el-input v-model="editForm.feeType" disabled />
        </el-form-item>
        <el-form-item label="名称">
          <el-input v-model="editForm.name" />
        </el-form-item>
        <el-form-item label="费率(%)">
          <el-input v-model="editForm.rate" />
        </el-form-item>
        <el-form-item label="最低费用">
          <el-input v-model="editForm.minFee" />
        </el-form-item>
        <el-form-item label="最高费用">
          <el-input v-model="editForm.maxFee" />
        </el-form-item>
        <el-form-item label="状态">
          <el-radio-group v-model="editForm.status">
            <el-radio value="ACTIVE">启用</el-radio>
            <el-radio value="INACTIVE">停用</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editDialog.visible = false">取消</el-button>
        <el-button type="primary" :loading="editSubmitting" @click="submitEdit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>
