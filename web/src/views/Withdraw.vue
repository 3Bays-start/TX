<template>
  <div class="page">
    <van-nav-bar title="提现" />
    <van-form @submit="onSubmit">
      <van-cell-group inset title="发起提现">
        <van-field
          v-model="form.amount"
          name="amount"
          label="金额"
          type="number"
          placeholder="请输入提现金额"
          :rules="[{ required: true, message: '请输入金额' }]"
        />
        <van-field
          v-model="form.usdt_address"
          name="usdt_address"
          label="USDT地址"
          placeholder="请输入 USDT 钱包地址（TRC20）"
          :rules="[
            { required: true, message: '请输入 USDT 钱包地址' },
            { validator: validateAddress, message: 'USDT 地址格式不正确' },
          ]"
        />
        <div class="actions">
          <van-button round block type="primary" native-type="submit" :loading="submitting">
            提交提现
          </van-button>
        </div>
      </van-cell-group>
    </van-form>

    <van-cell-group inset title="提现记录">
      <van-cell
        v-for="w in list"
        :key="w.id"
        :title="w.usdt_address"
        :label="`${formatTime(w.created_at)} · ${statusText(w.status)}`"
        :value="formatMoney(w.amount)"
      />
      <van-empty v-if="finished && !list.length" description="暂无提现记录" />
    </van-cell-group>
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
import { createWithdrawal, getWithdrawals } from '../api/finance'
import type { Withdrawal } from '../api/finance'
import { formatMoney, formatTime, statusText } from '../utils/format'

const form = ref({ amount: '', usdt_address: '' })
const submitting = ref(false)
const list = ref<Withdrawal[]>([])
const page = ref(1)
const pageSize = 10
const loading = ref(false)
const finished = ref(false)

onMounted(loadMore)

function validateAddress(value: string): boolean {
  return /^(T[A-Za-z0-9]{25,34}|0x[A-Za-f0-9]{40}|[A-Za-z0-9]{34})$/.test(value)
}

async function onSubmit() {
  if (Number(form.value.amount) <= 0) {
    showToast('请输入有效金额')
    return
  }
  submitting.value = true
  try {
    await createWithdrawal({ ...form.value })
    showToast('提交成功')
    form.value = { amount: '', usdt_address: '' }
    list.value = []
    page.value = 1
    finished.value = false
    loadMore()
  } catch (err) {
    showToast(err instanceof Error ? err.message : '提交失败')
  } finally {
    submitting.value = false
  }
}

async function loadMore() {
  if (loading.value || finished.value) return
  loading.value = true
  try {
    const res = await getWithdrawals({ page: page.value, page_size: pageSize })
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
</script>