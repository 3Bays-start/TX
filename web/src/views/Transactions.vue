<template>
  <div class="page">
    <van-nav-bar title="交易流水" />
    <van-cell
      v-for="t in list"
      :key="t.id"
      :title="t.business_type || '交易'"
      :label="`${formatTime(t.created_at)}${t.remark ? ' · ' + t.remark : ''}`"
    >
      <template #value>
        <span :class="amountClass(t)">{{ signed(t) }}</span>
      </template>
    </van-cell>
    <van-empty v-if="finished && !list.length" description="暂无流水" />
    <div v-if="list.length" class="load-more">
      <van-button v-if="!finished" size="small" plain :loading="loading" @click="loadMore">
        加载更多
      </van-button>
      <span v-else class="finished-text">没有更多了</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { showToast } from 'vant'
import { getTransactions } from '../api/account'
import type { TransactionRecord } from '../api/account'
import { formatTime } from '../utils/format'

const list = ref<TransactionRecord[]>([])
const page = ref(1)
const pageSize = 15
const loading = ref(false)
const finished = ref(false)

onMounted(loadMore)

async function loadMore() {
  if (loading.value || finished.value) return
  loading.value = true
  try {
    const res = await getTransactions({ page: page.value, page_size: pageSize })
    const items = res.items ?? []
    list.value.push(...items)
    if (items.length < pageSize || list.value.length >= (res.total ?? Number.MAX_SAFE_INTEGER)) {
      finished.value = true
    } else {
      page.value += 1
    }
  } catch (err) {
    showToast(err instanceof Error ? err.message : '加载失败')
  } finally {
    loading.value = false
  }
}

function signed(t: TransactionRecord): string {
  const n = Number(t.amount)
  if (Number.isNaN(n)) return String(t.amount)
  return `${n >= 0 ? '+' : '-'}¥${Math.abs(n).toLocaleString('zh-CN', { maximumFractionDigits: 2 })}`
}

function amountClass(t: TransactionRecord): string {
  const n = Number(t.amount)
  if (Number.isNaN(n)) return 'tx-amount'
  return n >= 0 ? 'tx-amount tx-in' : 'tx-amount tx-out'
}
</script>

<style scoped>
.tx-amount {
  font-weight: 600;
}

.tx-in {
  color: #ee0a24;
}

.tx-out {
  color: #1989fa;
}
</style>