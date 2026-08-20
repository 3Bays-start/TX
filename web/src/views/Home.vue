<template>
  <div class="page home">
    <van-nav-bar title="LX 平台">
      <template #right>
        <van-icon name="bullhorn-o" size="20" class="nav-bell" @click="router.push('/announcements')" />
      </template>
    </van-nav-bar>

    <div class="banner-area">
      <van-swipe v-if="banners.length" class="banner-swipe" :autoplay="4000" indicator-color="#fff">
        <van-swipe-item v-for="(b, i) in banners" :key="b.id" @click="onBannerClick(b)">
          <div v-if="b.image_url" class="banner-card banner-img-card">
            <img :src="b.image_url" class="banner-img" alt="" />
          </div>
          <div v-else class="banner-card" :style="{ background: bannerGradient(i) }">
            <div class="banner-title">{{ b.title }}</div>
            <div v-if="b.subtitle" class="banner-subtitle">{{ b.subtitle }}</div>
          </div>
        </van-swipe-item>
      </van-swipe>
    </div>

    <van-notice-bar v-if="announcements.length" left-icon="volume-o" :scrollable="true">
      {{ announcements[0].title }}
    </van-notice-bar>

    <div class="greeting-card">
      <div class="greeting-title">{{ greeting }}</div>
      <div class="greeting-sub">{{ greetingSub }}</div>
      <div v-if="!loggedIn" class="guest-actions">
        <van-button size="small" type="primary" round @click="router.push('/login')">
          登录
        </van-button>
        <van-button size="small" plain round @click="router.push('/register')">
          注册
        </van-button>
      </div>
    </div>

    <div class="section">
      <div class="section-title">援助中心</div>
      <div class="aid-grid">
        <div class="aid-card sell" @click="router.push('/aid-order?type=SELL')">
          <van-icon name="gold-coin-o" size="30" />
          <div class="aid-name">获得援助</div>
          <div class="aid-desc">卖出 · 排队撮合</div>
        </div>
        <div class="aid-card buy" @click="router.push('/aid-order?type=BUY')">
          <van-icon name="exchange" size="30" />
          <div class="aid-name">提供援助</div>
          <div class="aid-desc">买入 · 先支付</div>
        </div>
      </div>
    </div>

    <div v-if="loggedIn && recentOrders.length" class="section">
      <div class="section-title">
        历史订单
        <span class="section-more" @click="router.push('/orders')">查看全部</span>
      </div>
      <van-cell-group inset>
        <van-cell
          v-for="o in recentOrders"
          :key="o.id"
          :title="o.order_no || `#${o.id}`"
          :label="`${orderTypeText(o.order_type)} · ${formatMoney(o.total_amount)} · ${formatTime(o.created_at)}`"
          is-link
          @click="router.push(`/orders/${o.id}`)"
        >
          <template #value>
            <van-tag :type="statusTagType(o.status)">{{ statusText(o.status) }}</van-tag>
          </template>
        </van-cell>
      </van-cell-group>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { showToast } from 'vant'
import { getAnnouncements, getBanners } from '../api/notification'
import type { Announcement, Banner } from '../api/notification'
import { getOrders } from '../api/order'
import type { Order } from '../api/order'
import { getMe } from '../api/auth'
import { formatMoney, formatTime, statusTagType, statusText } from '../utils/format'

const router = useRouter()
const loggedIn = ref(!!localStorage.getItem('lx_token'))
const greeting = ref('欢迎来到 LX 平台')
const greetingSub = ref('登录后享受更多服务')
const announcements = ref<Announcement[]>([])
const banners = ref<Banner[]>([])
const recentOrders = ref<Order[]>([])

const gradients = [
  'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
  'linear-gradient(135deg, #f83600 0%, #f9d423 100%)',
  'linear-gradient(135deg, #a18cd1 0%, #fbc2eb 100%)',
  'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)',
]

onMounted(() => {
  loadAnnouncements()
  loadBanners()
  if (loggedIn.value) {
    loadGreeting()
    loadRecentOrders()
  }
})

function orderTypeText(t?: string): string {
  if (t === 'BUY') return '提供援助'
  if (t === 'SELL') return '获得援助'
  return '普通订单'
}

async function loadRecentOrders() {
  try {
    const res = await getOrders({ page: 1, page_size: 5 })
    recentOrders.value = res.items ?? []
  } catch {
    recentOrders.value = []
  }
}

async function loadAnnouncements() {
  try {
    announcements.value = await getAnnouncements()
  } catch {
    announcements.value = []
  }
}

async function loadBanners() {
  try {
    banners.value = await getBanners()
  } catch {
    banners.value = []
  }
}

async function loadGreeting() {
  try {
    const me = await getMe()
    greeting.value = `你好，${me.nickname || me.username}`
    greetingSub.value = me.credit_level_name ? `信用等级：${me.credit_level_name}（已完成 ${me.completed_order_count || 0} 笔订单）` : '欢迎回来'
  } catch {
    greeting.value = '欢迎来到 LX 平台'
  }
}

function bannerGradient(i: number): string {
  return gradients[i % gradients.length]
}

function onBannerClick(b: Banner) {
  if (b.link_type === 'LINK' && b.link_value) {
    router.push(b.link_value)
  } else if (b.link_type === 'NOTICE') {
    router.push('/announcements')
  } else {
    showToast(b.title)
  }
}
</script>

<style scoped>
.nav-bell {
  padding: 0 4px;
}

.banner-area {
  margin: 12px 12px 0;
}

.banner-swipe {
  border-radius: 12px;
  overflow: hidden;
}

.banner-card {
  height: 190px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #fff;
}

.banner-img-card {
  height: 190px;
}

.banner-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.banner-title {
  font-size: 20px;
  font-weight: 700;
  letter-spacing: 1px;
}

.banner-subtitle {
  font-size: 13px;
  opacity: 0.9;
  margin-top: 8px;
}

.greeting-card {
  margin: 16px;
  padding: 20px 16px;
  background: linear-gradient(135deg, #1989fa, #3ec8ff);
  border-radius: 12px;
  color: #fff;
}

.greeting-title {
  font-size: 18px;
  font-weight: 600;
}

.greeting-sub {
  font-size: 13px;
  opacity: 0.85;
  margin-top: 6px;
  margin-bottom: 12px;
}

.guest-actions {
  display: flex;
  gap: 12px;
}

.section {
  margin: 16px;
}

.section-title {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 12px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.section-more {
  font-size: 13px;
  font-weight: 400;
  color: #969799;
}

.aid-grid {
  display: flex;
  gap: 12px;
}

.aid-card {
  flex: 1;
  border-radius: 12px;
  padding: 20px 16px;
  color: #fff;
  text-align: center;
}

.aid-card.sell {
  background: linear-gradient(135deg, #ff976a, #ff6d6d);
}

.aid-card.buy {
  background: linear-gradient(135deg, #4facfe, #00c6ff);
}

.aid-name {
  font-size: 16px;
  font-weight: 600;
  margin-top: 8px;
}

.aid-desc {
  font-size: 12px;
  opacity: 0.85;
  margin-top: 4px;
}
</style>