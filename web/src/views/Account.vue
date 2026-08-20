<template>
  <div class="page">
    <van-nav-bar title="我的账户" />
    <div class="balance-card">
      <div class="balance-item">
        <div class="balance-label">可用</div>
        <div class="balance-value">{{ formatMoney(account?.available) }}</div>
      </div>
      <div class="balance-item">
        <div class="balance-label">冻结</div>
        <div class="balance-value">{{ formatMoney(account?.frozen) }}</div>
      </div>
      <div class="balance-item">
        <div class="balance-label">待入账</div>
        <div class="balance-value">{{ formatMoney(account?.pending) }}</div>
      </div>
    </div>

    <van-cell-group v-if="switchedFrom" inset>
      <van-cell center title="当前为切换登录状态" label="可一键返回自己的账号">
        <template #value>
          <van-button size="small" type="warning" plain @click="switchBack">返回上级账号</van-button>
        </template>
      </van-cell>
    </van-cell-group>

    <van-cell-group inset>
      <van-cell title="交易流水" is-link to="/account/transactions" />
      <van-cell title="我要提现" is-link to="/withdraw" />
    </van-cell-group>

    <van-cell-group inset title="推广记录">
      <van-cell
        v-for="r in promo"
        :key="r.id"
        :title="r.invited_phone || '推广记录'"
        :value="formatMoney(r.reward)"
        :label="formatTime(r.created_at)"
      />
      <van-empty v-if="!promo.length" description="暂无推广记录" />
    </van-cell-group>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { showToast } from 'vant'
import { getAccounts } from '../api/account'
import type { AccountSummary } from '../api/account'
import { getPromotionRecords } from '../api/finance'
import type { PromotionRecord } from '../api/finance'
import { useAuthStore } from '../stores/auth'
import { formatMoney, formatTime } from '../utils/format'

const router = useRouter()
const authStore = useAuthStore()

const account = ref<AccountSummary | null>(null)
const promo = ref<PromotionRecord[]>([])
const switchedFrom = ref(!!localStorage.getItem('lx_switch_from'))

onMounted(() => {
  loadAccount()
  loadPromo()
})

async function loadAccount() {
  try {
    account.value = await getAccounts()
  } catch (err) {
    showToast(err instanceof Error ? err.message : '加载失败')
  }
}

async function loadPromo() {
  try {
    const res = await getPromotionRecords({ page: 1, page_size: 10 })
    promo.value = res.items ?? []
  } catch {
    promo.value = []
  }
}

function switchBack() {
  const saved = localStorage.getItem('lx_switch_from')
  if (!saved) {
    showToast('没有可返回的账号')
    return
  }
  authStore.setToken(saved)
  localStorage.removeItem('lx_switch_from')
  switchedFrom.value = false
  showToast('已返回上级账号')
  router.push('/home')
}
</script>

<style scoped>
.balance-card {
  display: flex;
  justify-content: space-around;
  margin: 16px;
  padding: 20px 12px;
  background: linear-gradient(135deg, #1989fa, #3ec8ff);
  border-radius: 12px;
  color: #fff;
}

.balance-label {
  font-size: 13px;
  opacity: 0.85;
  text-align: center;
}

.balance-value {
  font-size: 18px;
  font-weight: 600;
  margin-top: 6px;
  text-align: center;
}
</style>