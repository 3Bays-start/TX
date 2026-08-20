<template>
  <div class="page">
    <van-nav-bar title="援助下单" />

    <div class="seg">
      <div
        class="seg-item"
        :class="{ active: direction === 'BUY' }"
        @click="direction = 'BUY'"
      >
        <div class="seg-title">提供援助</div>
        <div class="seg-sub">买入 · 先支付后撮合</div>
      </div>
      <div
        class="seg-item"
        :class="{ active: direction === 'SELL' }"
        @click="direction = 'SELL'"
      >
        <div class="seg-title">获得援助</div>
        <div class="seg-sub">卖出 · 排队等待撮合</div>
      </div>
    </div>

    <van-form @submit="onSubmit">
      <van-cell-group inset>
        <van-field
          v-model="amount"
          name="amount"
          label="金额"
          type="number"
          placeholder="请输入援助金额"
          :rules="[{ required: true, message: '请输入金额' }]"
        />
        <van-field v-model="remark" name="remark" label="备注" placeholder="选填" />
      </van-cell-group>
      <div class="actions">
        <van-button
          round
          block
          color="linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)"
          native-type="submit"
          :loading="submitting"
        >
          {{ direction === 'BUY' ? '确认提供援助' : '确认获得援助' }}
        </van-button>
      </div>
    </van-form>

    <van-cell-group inset class="notice">
      <van-cell title="提供援助（买入）" label="先支付订单金额与服务费，进入撮合队列匹配卖出方" />
      <van-cell title="获得援助（卖出）" label="发布需求进入撮合队列，匹配成功后由买入方付款" />
    </van-cell-group>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { showToast } from 'vant'
import { createOrder } from '../api/order'
import type { OrderType } from '../api/order'

const route = useRoute()
const router = useRouter()

const direction = ref<OrderType>(route.query.type === 'SELL' ? 'SELL' : 'BUY')
const amount = ref('')
const remark = ref('')
const submitting = ref(false)

async function onSubmit() {
  submitting.value = true
  try {
    const order = await createOrder({
      order_type: direction.value,
      amount: amount.value,
      remark: remark.value || undefined,
    })
    showToast('下单成功')
    router.push(`/orders/${order.id}`)
  } catch (err) {
    showToast(err instanceof Error ? err.message : '下单失败')
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.seg {
  display: flex;
  gap: 12px;
  margin: 16px;
}

.seg-item {
  flex: 1;
  padding: 16px;
  border-radius: 12px;
  background: #fff;
  border: 1px solid #ebedf0;
  text-align: center;
  transition: all 0.2s;
}

.seg-item.active {
  border-color: #1989fa;
  background: linear-gradient(135deg, #1989fa, #3ec8ff);
  color: #fff;
}

.seg-title {
  font-size: 17px;
  font-weight: 600;
}

.seg-sub {
  font-size: 12px;
  margin-top: 6px;
  opacity: 0.85;
}

.actions {
  margin: 24px 16px;
}

.notice {
  margin: 16px;
}
</style>