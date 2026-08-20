<template>
  <div class="page">
    <van-nav-bar title="订单详情" />
    <div v-if="order">
      <div class="detail-head">
        <van-tag size="large" :type="statusTagType(order.status)">
          {{ statusText(order.status) }}
        </van-tag>
      </div>
      <van-cell-group inset>
        <van-cell title="订单号" :value="order.order_no || `#${order.id}`" />
        <van-cell title="方向" :value="order.order_type === 'BUY' ? '提供援助（买入）' : order.order_type === 'SELL' ? '获得援助（卖出）' : order.order_type || '-'" />
        <van-cell title="金额" :value="formatMoney(order.total_amount)" />
        <van-cell v-if="order.service_fee" title="服务费" :value="formatMoney(order.service_fee)" />
        <van-cell v-if="order.payable_amount" title="应付" :value="formatMoney(order.payable_amount)" />
        <van-cell v-if="order.matched_amount" title="已撮合" :value="formatMoney(order.matched_amount)" />
        <van-cell title="创建时间" :value="formatTime(order.created_at)" />
        <van-cell title="备注" :value="order.remark || '-'" />
      </van-cell-group>

      <div v-if="order.status_logs?.length" class="section">
        <div class="section-title">状态记录</div>
        <van-steps direction="vertical" :active="order.status_logs.length - 1">
          <van-step v-for="(log, i) in order.status_logs" :key="i">
            <div>
              {{ statusText(log.to_status) }}
              <span class="muted">{{ formatTime(log.created_at) }}</span>
            </div>
            <div v-if="log.note" class="muted">{{ log.note }}</div>
          </van-step>
        </van-steps>
      </div>

      <div v-if="order.matches?.length" class="section">
        <div class="section-title">撮合记录</div>
        <van-cell
          v-for="(m, i) in order.matches"
          :key="i"
          :title="m.matched_order_no || `撮合 ${i + 1}`"
          :value="formatMoney(m.amount)"
          :label="formatTime(m.created_at)"
        />
      </div>

      <div v-if="canUploadProof" class="section">
        <div class="section-title">服务凭证</div>
        <van-uploader
          v-model="proofFiles"
          :max-count="9"
          :after-read="onAfterRead"
          :disabled="proofSubmitting"
          multiple
          @delete="onDeleteProof"
        />
        <div class="muted">撮合完成后请上传服务凭证（图片或 PDF），作为服务完成依据</div>
      </div>

      <div class="actions">
        <van-button
          v-if="order.order_type === 'BUY' && order.status === 'WAITING_PAYMENT'"
          block type="primary" round :loading="paying" @click="pay"
        >
          支付
        </van-button>
        <van-button
          v-if="order.order_type !== 'BUY' && order.order_type !== 'SELL'"
          block type="danger" plain round :loading="cancelling" @click="cancel"
        >
          取消订单
        </van-button>
        <van-button v-if="order.order_type !== 'SELL'" block type="success" plain round :loading="reserving" @click="reserve">
          预约
        </van-button>
        <van-button v-if="order.order_type === 'BUY' || order.order_type === 'SELL'" block type="primary" plain round @click="router.push(`/orders/${order.id}/match`)">
          查看撮合
        </van-button>
      </div>
    </div>
    <van-empty v-else-if="!loading" description="未找到订单" />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import type { UploaderFileListItem } from 'vant'
import { showToast } from 'vant'
import { cancelOrder, getOrder, payOrder, submitProof, uploadFile } from '../api/order'
import type { OrderDetail } from '../api/order'
import { createReservation } from '../api/reservation'
import { formatMoney, formatTime, statusTagType, statusText } from '../utils/format'

const route = useRoute()
const router = useRouter()
const orderId = Number(route.params.id)
const order = ref<OrderDetail | null>(null)
const loading = ref(false)
const paying = ref(false)
const cancelling = ref(false)
const reserving = ref(false)
const proofFiles = ref<UploaderFileListItem[]>([])
const proofSubmitting = ref(false)

const canUploadProof = computed(() => {
  const status = order.value?.status ?? ''
  return (
    order.value?.order_type !== 'SELL' &&
    ['FULL_MATCHED', 'PROCESSING', 'COMPLETED'].includes(status)
  )
})

onMounted(load)

async function load() {
  loading.value = true
  try {
    order.value = await getOrder(orderId)
    syncProofFiles()
  } catch (err) {
    showToast(err instanceof Error ? err.message : '加载失败')
  } finally {
    loading.value = false
  }
}

function syncProofFiles() {
  proofFiles.value = (order.value?.proof_urls ?? []).map((url) => ({ url, status: 'done' }))
}

async function onAfterRead(item: UploaderFileListItem | UploaderFileListItem[]) {
  const list = Array.isArray(item) ? item : [item]
  for (const it of list) {
    if (!it.file) continue
    proofSubmitting.value = true
    try {
      const { url } = await uploadFile(it.file)
      it.url = url
      it.status = 'done'
      await saveProof()
      showToast('上传成功')
    } catch (err) {
      showToast(err instanceof Error ? err.message : '上传失败')
      proofFiles.value = proofFiles.value.filter((f) => f !== it)
    } finally {
      proofSubmitting.value = false
    }
  }
}

async function saveProof() {
  const urls = proofFiles.value.map((f) => f.url).filter((u): u is string => !!u)
  await submitProof(orderId, urls)
  order.value = await getOrder(orderId)
}

async function onDeleteProof() {
  try {
    await saveProof()
  } catch (err) {
    showToast(err instanceof Error ? err.message : '保存失败')
  }
}

async function pay() {
  paying.value = true
  try {
    await payOrder(orderId)
    showToast('支付成功')
    load()
  } catch (err) {
    showToast(err instanceof Error ? err.message : '支付失败')
  } finally {
    paying.value = false
  }
}

async function cancel() {
  cancelling.value = true
  try {
    await cancelOrder(orderId)
    showToast('已取消')
    load()
  } catch (err) {
    showToast(err instanceof Error ? err.message : '取消失败')
  } finally {
    cancelling.value = false
  }
}

async function reserve() {
  reserving.value = true
  try {
    await createReservation({ order_id: orderId })
    showToast('预约成功')
  } catch (err) {
    showToast(err instanceof Error ? err.message : '预约失败')
  } finally {
    reserving.value = false
  }
}
</script>

<style scoped>
.detail-head {
  padding: 20px 16px;
  text-align: center;
}
</style>