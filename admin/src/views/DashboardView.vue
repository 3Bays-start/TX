<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import * as echarts from 'echarts'
import { fetchDashboard } from '@/api/admin'
import type { DashboardData } from '@/api/types'
import { formatAmount } from '@/utils/format'

const loading = ref(false)
const data = ref<DashboardData | null>(null)

const userChartRef = ref<HTMLDivElement>()
const orderChartRef = ref<HTMLDivElement>()
let userChart: ReturnType<typeof echarts.init> | null = null
let orderChart: ReturnType<typeof echarts.init> | null = null

const cards = computed(() => {
  const d = data.value
  return [
    { label: '用户总数', value: String(d?.user_total ?? 0), color: '#409eff' },
    { label: '今日新增用户', value: String(d?.user_today ?? 0), color: '#67c23a' },
    { label: '7日活跃用户', value: String(d?.active_users ?? 0), color: '#e6a23c' },
    { label: '订单总数', value: String(d?.order_total ?? 0), color: '#909399' },
    { label: '今日订单', value: String(d?.order_today ?? 0), color: '#f56c6c' },
    { label: '待撮合订单', value: String(d?.waiting_match ?? 0), color: '#e6a23c' },
    { label: '异常订单', value: String(d?.abnormal_orders ?? 0), color: '#f56c6c' },
    { label: '待处理申诉', value: String(d?.appeal_pending ?? 0), color: '#409eff' },
    { label: '待审核提现', value: String(d?.withdrawal_pending ?? 0), color: '#67c23a' },
    { label: '累计服务费', value: formatAmount(d?.service_fee_total), color: '#7928ca' },
  ]
})

function last7days(): string[] {
  const labels: string[] = []
  const now = new Date()
  for (let i = 6; i >= 0; i--) {
    const t = new Date(now.getFullYear(), now.getMonth(), now.getDate() - i)
    labels.push(`${t.getMonth() + 1}/${t.getDate()}`)
  }
  return labels
}

function renderCharts() {
  const d = data.value
  if (!d) return
  const labels = last7days()

  if (userChartRef.value) {
    if (!userChart) userChart = echarts.init(userChartRef.value)
    userChart.setOption({
      tooltip: { trigger: 'axis' },
      grid: { left: 40, right: 16, top: 30, bottom: 28 },
      xAxis: { type: 'category', data: labels },
      yAxis: { type: 'value', minInterval: 1 },
      series: [
        {
          name: '新增用户',
          type: 'line',
          smooth: true,
          areaStyle: { opacity: 0.15 },
          data: d.charts.user_growth,
          itemStyle: { color: '#409eff' },
        },
      ],
    })
  }

  if (orderChartRef.value) {
    if (!orderChart) orderChart = echarts.init(orderChartRef.value)
    orderChart.setOption({
      tooltip: { trigger: 'axis' },
      grid: { left: 40, right: 16, top: 30, bottom: 28 },
      xAxis: { type: 'category', data: labels },
      yAxis: { type: 'value', minInterval: 1 },
      series: [
        {
          name: '订单数量',
          type: 'line',
          smooth: true,
          areaStyle: { opacity: 0.15 },
          data: d.charts.order_trend,
          itemStyle: { color: '#67c23a' },
        },
      ],
    })
  }
}

function handleResize() {
  userChart?.resize()
  orderChart?.resize()
}

async function load() {
  loading.value = true
  try {
    data.value = await fetchDashboard()
    await nextTick()
    renderCharts()
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  load()
  window.addEventListener('resize', handleResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  userChart?.dispose()
  orderChart?.dispose()
  userChart = null
  orderChart = null
})
</script>

<template>
  <div class="page" v-loading="loading">
    <el-row :gutter="16">
      <el-col v-for="card in cards" :key="card.label" :xs="12" :sm="8" :md="6" :lg="4">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-label">{{ card.label }}</div>
          <div class="stat-value" :style="{ color: card.color }">{{ card.value }}</div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16" class="chart-row">
      <el-col :xs="24" :md="12">
        <el-card shadow="never">
          <template #header><span class="chart-title">近 7 天用户增长</span></template>
          <div ref="userChartRef" class="chart-box"></div>
        </el-card>
      </el-col>
      <el-col :xs="24" :md="12">
        <el-card shadow="never">
          <template #header><span class="chart-title">近 7 天订单趋势</span></template>
          <div ref="orderChartRef" class="chart-box"></div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<style scoped>
.stat-card {
  margin-bottom: 16px;
}

.stat-label {
  font-size: 13px;
  color: #909399;
  margin-bottom: 8px;
}

.stat-value {
  font-size: 22px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  word-break: break-all;
}

.chart-row {
  margin-top: 4px;
}

.chart-title {
  font-weight: 600;
}

.chart-box {
  height: 320px;
}
</style>
