<template>
  <div class="page">
    <van-nav-bar title="订单撮合" />
    <div v-if="info">
      <van-cell-group inset>
        <van-cell title="订单状态" :value="statusText(info.status)" />
        <van-cell title="目标金额" :value="formatMoney(info.target_amount)" />
        <van-cell title="已撮合" :value="formatMoney(info.matched_amount)" />
        <van-cell title="剩余金额" :value="formatMoney(info.remaining_amount)" />
      </van-cell-group>
      <div class="section">
        <div class="section-title">撮合进度</div>
        <van-progress :percentage="progress" stroke-width="8" color="#1989fa" />
      </div>
      <div class="section">
        <div class="section-title">撮合明细</div>
        <van-cell
          v-for="(m, i) in info.matches"
          :key="i"
          :title="m.matched_order_no || `撮合 ${i + 1}`"
          :value="formatMoney(m.amount)"
          :label="formatTime(m.created_at)"
        />
        <van-empty v-if="!info.matches?.length" description="暂无撮合记录" />
      </div>
    </div>
    <van-empty v-else-if="!loading" description="暂无撮合数据" />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { showToast } from 'vant'
import { getOrderMatch } from '../api/order'
import type { OrderMatchInfo } from '../api/order'
import { formatMoney, formatTime, statusText } from '../utils/format'

const route = useRoute()
const orderId = Number(route.params.id)
const info = ref<OrderMatchInfo | null>(null)
const loading = ref(false)

onMounted(load)

async function load() {
  loading.value = true
  try {
    info.value = await getOrderMatch(orderId)
  } catch (err) {
    showToast(err instanceof Error ? err.message : '加载失败')
  } finally {
    loading.value = false
  }
}

const progress = computed(() => {
  const target = Number(info.value?.target_amount ?? 0)
  const matched = Number(info.value?.matched_amount ?? 0)
  if (target <= 0) return 0
  return Math.min(100, Math.round((matched / target) * 100))
})
</script>