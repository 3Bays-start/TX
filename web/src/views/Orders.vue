<template>
  <div class="page">
    <van-nav-bar title="订单" />
    <van-tabs v-model:active="activeTab" @change="onTabChange">
      <van-tab v-for="t in statusTabs" :key="t.value" :title="t.label" :name="t.value" />
    </van-tabs>
    <div
      v-for="o in list"
      :key="o.id"
      class="order-card"
      @click="router.push(`/orders/${o.id}`)"
    >
      <div class="order-head">
        <span class="order-no">{{ o.order_no || `#${o.id}` }}</span>
        <van-tag :type="statusTagType(o.status)">{{ statusText(o.status) }}</van-tag>
      </div>
      <div class="order-body">
        <span>{{ o.order_type === 'BUY' ? '提供援助' : o.order_type === 'SELL' ? '获得援助' : o.product_name || '未知产品' }}</span>
        <span class="order-amount">{{ formatMoney(o.total_amount) }}</span>
      </div>
      <div class="order-foot">{{ formatTime(o.created_at) }}</div>
    </div>
    <van-empty v-if="finished && !list.length" description="暂无订单" />
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
import { useRouter } from 'vue-router'
import { showToast } from 'vant'
import { getOrders } from '../api/order'
import type { Order } from '../api/order'
import { formatMoney, formatTime, statusTagType, statusText } from '../utils/format'

const router = useRouter()
const statusTabs = [
  { label: '全部', value: 'ALL' },
  { label: '待撮合', value: 'WAITING_MATCH' },
  { label: '部分撮合', value: 'PARTIAL_MATCHED' },
  { label: '已撮合', value: 'FULL_MATCHED' },
  { label: '已支付', value: 'PAID' },
]
const activeTab = ref('ALL')
const list = ref<Order[]>([])
const page = ref(1)
const pageSize = 10
const loading = ref(false)
const finished = ref(false)

onMounted(loadMore)

async function loadMore() {
  if (loading.value || finished.value) return
  loading.value = true
  try {
    const status = activeTab.value === 'ALL' ? undefined : activeTab.value
    const res = await getOrders({ status, page: page.value, page_size: pageSize })
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

function onTabChange() {
  list.value = []
  page.value = 1
  finished.value = false
  loading.value = false
  loadMore()
}
</script>

<style scoped>
.order-card {
  margin: 10px 12px;
  background: #fff;
  border-radius: 10px;
  padding: 12px;
}

.order-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.order-no {
  color: #969799;
  font-size: 13px;
}

.order-body {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.order-amount {
  color: #ee0a24;
  font-weight: 600;
}

.order-foot {
  margin-top: 8px;
  color: #969799;
  font-size: 12px;
}
</style>