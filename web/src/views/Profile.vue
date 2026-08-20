<template>
  <div class="page">
    <van-nav-bar title="我的" />
    <div class="user-card">
      <van-image round width="56" height="56" :src="me?.avatar || ''">
        <template #error>
          <van-icon name="manager" size="28" />
        </template>
        <template #loading>
          <van-icon name="manager" size="28" />
        </template>
      </van-image>
      <div class="user-info">
        <div class="user-name">{{ me?.nickname || me?.username || '未登录' }}</div>
        <div class="user-meta">
          <van-tag plain>{{ me?.username || '' }}</van-tag>
          <van-tag type="warning">信用 {{ me?.credit_level_name || '普通信用' }}</van-tag>
        </div>
      </div>
    </div>

    <van-cell-group inset>
      <van-cell title="信用等级" icon="diamond-o" :value="me?.credit_level_name || '-'" is-link to="/credit" />
      <van-cell title="我的团队" icon="friends-o" is-link to="/team" />
      <van-cell title="我的账户" icon="balance-o" is-link to="/account" />
      <van-cell title="提现" icon="cash-back-record-o" is-link to="/withdraw" />
      <van-cell title="通知中心" icon="bell-o" is-link to="/notifications" />
      <van-cell title="安全设置" icon="shield-o" is-link to="/security" />
      <van-cell title="客服中心" icon="service-o" is-link to="/customer-service" />
      <van-cell title="申诉" icon="warning-o" is-link to="/appeal" />
    </van-cell-group>

    <div class="actions">
      <van-button block round type="danger" plain @click="logout">退出登录</van-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { showToast } from 'vant'
import { getMe } from '../api/user'
import type { UserProfile } from '../api/user'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const authStore = useAuthStore()
const me = ref<UserProfile | null>(null)

onMounted(load)

async function load() {
  try {
    me.value = await getMe()
  } catch (err) {
    showToast(err instanceof Error ? err.message : '加载失败')
  }
}

function logout() {
  authStore.clearToken()
  localStorage.removeItem('lx_switch_from')
  router.push('/login')
}
</script>

<style scoped>
.user-card {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 16px;
  padding: 16px;
  background: linear-gradient(135deg, #1989fa, #3ec8ff);
  border-radius: 12px;
  color: #fff;
}

.user-name {
  font-size: 17px;
  font-weight: 600;
}

.user-meta {
  margin-top: 8px;
  display: flex;
  gap: 8px;
}
</style>