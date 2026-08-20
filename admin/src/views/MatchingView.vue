<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import type { FormInstance } from 'element-plus'
import { ElMessage } from 'element-plus'
import { autoMatch, listMatching, listMatchingJobs, manualMatchBatch } from '@/api/admin'
import type { MatchingItem, MatchingJob } from '@/api/types'
import { useAuthStore } from '@/stores/auth'
import { formatAmount, formatDateTime, statusText, tagType } from '@/utils/format'

const auth = useAuthStore()
const activeTab = ref('queue')
const loading = ref(false)
const autoMatching = ref(false)

// ===== 撮合队列 =====
const queue = ref<MatchingItem[]>([])
const total = ref(0)
const query = reactive({ status: '', page: 1, pageSize: 10 })
const selection = ref<MatchingItem[]>([])

async function loadQueue() {
  loading.value = true
  try {
    const params: { page: number; page_size: number; status?: string } = {
      page: query.page,
      page_size: query.pageSize,
    }
    if (query.status) params.status = query.status
    const res = await listMatching(params)
    queue.value = res.items
    total.value = res.total
  } finally {
    loading.value = false
  }
}

// ===== 撮合任务 =====
const jobs = ref<MatchingJob[]>([])
const jobTotal = ref(0)
const jobPage = ref(1)
const jobPageSize = ref(10)

async function loadJobs() {
  loading.value = true
  try {
    const res = await listMatchingJobs({ page: jobPage.value, page_size: jobPageSize.value })
    jobs.value = res.items
    jobTotal.value = res.total
  } finally {
    loading.value = false
  }
}

function handleTabChange() {
  if (activeTab.value === 'jobs') loadJobs()
  else loadQueue()
}

// ===== 批量撮合 =====
const selectedBuyIds = computed(() =>
  selection.value.filter((r) => r.order_type === 'BUY').map((r) => r.id),
)
const selectedSellIds = computed(() =>
  selection.value.filter((r) => r.order_type === 'SELL').map((r) => r.id),
)
const canManualMatch = computed(
  () => selectedBuyIds.value.length > 0 && selectedSellIds.value.length > 0,
)

const matchDialog = reactive({ visible: false })
const matchFormRef = ref<FormInstance>()
const matchForm = reactive({ reason: '' })
const matchSubmitting = ref(false)

function openBatchMatch() {
  matchForm.reason = ''
  matchDialog.visible = true
}

async function submitBatchMatch() {
  matchSubmitting.value = true
  try {
    const res = await manualMatchBatch({
      buy_order_ids: selectedBuyIds.value,
      sell_order_ids: selectedSellIds.value,
      reason: matchForm.reason || undefined,
    })
    ElMessage.success(`成功撮合 ${res.matched} 笔`)
    matchDialog.visible = false
    selection.value = []
    loadQueue()
    loadJobs()
  } finally {
    matchSubmitting.value = false
  }
}

async function runAutoMatch() {
  autoMatching.value = true
  try {
    const res = await autoMatch()
    ElMessage.success(
      `自动撮合完成：处理 ${res.processed}，成功 ${res.matched}，失败 ${res.failed}`,
    )
    loadQueue()
    loadJobs()
  } finally {
    autoMatching.value = false
  }
}

onMounted(loadQueue)
</script>

<template>
  <div class="page">
    <el-card shadow="never">
      <el-tabs v-model="activeTab" @tab-change="handleTabChange">
        <el-tab-pane label="撮合队列" name="queue">
          <div class="filter-bar">
            <el-select v-model="query.status" placeholder="撮合状态" clearable style="width: 160px">
              <el-option label="待撮合" value="WAITING_MATCH" />
              <el-option label="部分撮合" value="PARTIAL_MATCHED" />
              <el-option label="已撮合" value="FULL_MATCHED" />
            </el-select>
            <el-button type="primary" @click="query.page = 1; loadQueue()">查询</el-button>
            <div v-if="auth.hasPerm('order:match')" class="filter-actions">
              <el-button type="primary" plain :loading="autoMatching" @click="runAutoMatch">
                自动撮合
              </el-button>
              <el-tooltip
                :disabled="canManualMatch"
                content="请同时勾选买入与卖出订单"
                placement="top"
              >
                <el-button :disabled="!canManualMatch" @click="openBatchMatch">手动撮合所选</el-button>
              </el-tooltip>
            </div>
          </div>

          <el-table
            v-loading="loading"
            :data="queue"
            stripe
            @selection-change="(rows: MatchingItem[]) => (selection = rows)"
          >
            <el-table-column type="selection" width="50" />
            <el-table-column prop="order_no" label="订单号" width="210" />
            <el-table-column label="用户" min-width="140">
              <template #default="{ row }">
                <div class="user-cell">
                  <div class="user-name">{{ row.user_nickname || row.user_username || `用户${row.user_id}` }}</div>
                  <div class="user-acct">{{ row.user_phone }}</div>
                </div>
              </template>
            </el-table-column>
            <el-table-column label="类型" width="90">
              <template #default="{ row }">
                <el-tag :type="tagType(row.order_type)" size="small">{{ statusText(row.order_type) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="目标金额" width="130">
              <template #default="{ row }"><span class="money">{{ formatAmount(row.target_amount) }}</span></template>
            </el-table-column>
            <el-table-column label="已撮合" width="130">
              <template #default="{ row }"><span class="money">{{ formatAmount(row.matched_amount) }}</span></template>
            </el-table-column>
            <el-table-column label="剩余金额" width="130">
              <template #default="{ row }"><span class="money">{{ formatAmount(row.remaining_amount) }}</span></template>
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
              v-model:current-page="query.page"
              v-model:page-size="query.pageSize"
              :total="total"
              :page-sizes="[10, 20, 50, 100]"
              layout="total, sizes, prev, pager, next"
              @size-change="loadQueue"
              @current-change="loadQueue"
            />
          </div>
        </el-tab-pane>

        <el-tab-pane label="撮合任务" name="jobs">
          <el-table v-loading="loading" :data="jobs" stripe>
            <el-table-column prop="job_id" label="任务ID" width="220" />
            <el-table-column label="开始时间" width="180">
              <template #default="{ row }">{{ formatDateTime(row.start_time) }}</template>
            </el-table-column>
            <el-table-column label="结束时间" width="180">
              <template #default="{ row }">{{ formatDateTime(row.end_time) }}</template>
            </el-table-column>
            <el-table-column prop="processed_count" label="处理数量" width="110" />
            <el-table-column label="成功" width="90">
              <template #default="{ row }"><span class="money" style="color: #67c23a">{{ row.success_count }}</span></template>
            </el-table-column>
            <el-table-column label="失败" width="90">
              <template #default="{ row }"><span class="money" style="color: #f56c6c">{{ row.failed_count }}</span></template>
            </el-table-column>
            <el-table-column label="状态" width="110">
              <template #default="{ row }">
                <el-tag :type="tagType(row.status)" size="small">{{ statusText(row.status) }}</el-tag>
              </template>
            </el-table-column>
          </el-table>
          <div class="pager">
            <el-pagination
              v-model:current-page="jobPage"
              v-model:page-size="jobPageSize"
              :total="jobTotal"
              layout="total, prev, pager, next"
              @current-change="loadJobs"
            />
          </div>
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <!-- 手动撮合所选 -->
    <el-dialog v-model="matchDialog.visible" title="手动撮合所选" width="480px">
      <el-form ref="matchFormRef" :model="matchForm" label-width="80px">
        <el-form-item label="买入订单">
          <span>已选择 {{ selectedBuyIds.length }} 笔</span>
        </el-form-item>
        <el-form-item label="卖出订单">
          <span>已选择 {{ selectedSellIds.length }} 笔</span>
        </el-form-item>
        <el-form-item label="原因">
          <el-input v-model="matchForm.reason" type="textarea" :rows="3" placeholder="可选" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="matchDialog.visible = false">取消</el-button>
        <el-button type="primary" :loading="matchSubmitting" @click="submitBatchMatch">确认撮合</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.filter-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
  margin-bottom: 16px;
}

.filter-actions {
  margin-left: auto;
  display: flex;
  gap: 8px;
}

.user-cell .user-name {
  font-weight: 500;
}

.user-cell .user-acct {
  font-size: 12px;
  color: #909399;
}
</style>