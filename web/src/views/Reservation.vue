<template>
  <div class="page">
    <van-nav-bar title="预约" />
    <van-form @submit="submitReservation">
      <van-cell-group inset title="新建预约">
        <van-field name="order_type" label="订单类型">
          <template #input>
            <van-radio-group v-model="form.order_type" direction="horizontal">
              <van-radio name="BUY">买入</van-radio>
              <van-radio name="SELL">卖出</van-radio>
            </van-radio-group>
          </template>
        </van-field>
        <van-field
          v-model="form.amount"
          name="amount"
          label="金额"
          type="number"
          placeholder="请输入金额"
          :rules="[{ required: true, message: '请输入金额' }]"
        />
        <van-field
          v-model="form.reservation_time"
          name="reservation_time"
          label="预约时间"
          placeholder="选填"
        />
        <van-field v-model="form.remark" name="remark" label="备注" placeholder="选填" />
      </van-cell-group>
      <div class="actions">
        <van-button round block type="primary" native-type="submit" :loading="submitting">
          提交预约
        </van-button>
      </div>
    </van-form>

    <van-cell-group inset title="我的预约">
      <van-cell
        v-for="r in reservations"
        :key="r.id"
        :title="r.product_name || `预约 #${r.id}`"
        :label="`${formatTime(r.reservation_time)} · ${statusText(r.status)}`"
      >
        <template #value>
          <span v-if="matchMap[r.id]" class="match-text">{{ matchStatus(r.id) }}</span>
          <van-button v-else size="mini" type="primary" plain @click="loadStatus(r)">
            查看撮合
          </van-button>
        </template>
      </van-cell>
      <van-empty v-if="!reservations.length" description="暂无预约" />
    </van-cell-group>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { showToast } from 'vant'
import { createOrder } from '../api/order'
import {
  createReservation,
  getMatchingStatus,
  getReservations,
} from '../api/reservation'
import type { MatchingStatus, Reservation } from '../api/reservation'
import { formatTime, statusText } from '../utils/format'

const router = useRouter()

const submitting = ref(false)
const form = ref({
  order_type: 'BUY',
  amount: '',
  reservation_time: '',
  remark: '',
})

const reservations = ref<Reservation[]>([])
const matchMap = ref<Record<number, MatchingStatus | undefined>>({})

onMounted(loadReservations)

async function submitReservation() {
  submitting.value = true
  try {
    const order = await createOrder({
      order_type: form.value.order_type as 'BUY' | 'SELL',
      amount: form.value.amount || undefined,
      reservation_time: form.value.reservation_time || undefined,
      remark: form.value.remark || undefined,
    })
    await createReservation({ order_id: order.id })
    showToast('预约成功')
    router.push('/orders')
  } catch (err) {
    showToast(err instanceof Error ? err.message : '预约失败')
  } finally {
    submitting.value = false
  }
}

async function loadReservations() {
  try {
    const items = await getReservations()
    reservations.value = items
    await Promise.allSettled(items.filter((r) => r.order_id).map((r) => loadStatus(r)))
  } catch (err) {
    showToast(err instanceof Error ? err.message : '加载失败')
  }
}

async function loadStatus(r: Reservation) {
  if (!r.order_id) return
  try {
    matchMap.value[r.id] = await getMatchingStatus(r.order_id)
  } catch {
    matchMap.value[r.id] = undefined
  }
}

function matchStatus(id: number): string {
  return statusText(matchMap.value[id]?.status ?? '')
}
</script>

<style scoped>
.match-text {
  color: #1989fa;
  font-size: 13px;
}
</style>