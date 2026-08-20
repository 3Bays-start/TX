<template>
  <div class="login-page">
    <div class="hero">
      <div class="logo">LX</div>
      <h1 class="app-name">LX 平台</h1>
      <p class="slogan">订单撮合 · 会员服务 · 值得信赖</p>
    </div>

    <div class="card">
      <van-form @submit="onSubmit">
        <van-cell-group inset>
          <van-field
            v-model="username"
            name="username"
            left-icon="contact-o"
            label="账号"
            placeholder="请输入账号"
            clearable
            :rules="[{ required: true, message: '请输入账号' }]"
          />
          <van-field
            v-model="password"
            type="password"
            name="password"
            left-icon="lock"
            label="密码"
            placeholder="请输入密码"
            autocomplete="current-password"
            :rules="[{ required: true, message: '请输入密码' }]"
          />
        </van-cell-group>
        <div class="actions">
          <van-button
            round
            block
            color="linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)"
            native-type="submit"
            :loading="loading"
          >
            登 录
          </van-button>
        </div>
      </van-form>

      <div class="footer">
        <span class="muted">还没有账号？</span>
        <router-link to="/register" class="link">立即注册</router-link>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { showToast } from 'vant'
import { login } from '../api/auth'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const username = ref('')
const password = ref('')
const loading = ref(false)

async function onSubmit() {
  loading.value = true
  try {
    const res = await login({ username: username.value, password: password.value })
    authStore.setToken(res.access_token)
    showToast('登录成功')
    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : '/home'
    router.push(redirect)
  } catch (err) {
    showToast(err instanceof Error ? err.message : '登录失败')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 0 24px;
  background: linear-gradient(160deg, #0f2027 0%, #203a43 45%, #2c5364 100%);
  box-sizing: border-box;
}

.hero {
  text-align: center;
  padding: 8px 0 40px;
}

.logo {
  width: 72px;
  height: 72px;
  margin: 0 auto 16px;
  border-radius: 20px;
  background: linear-gradient(135deg, #4facfe, #00f2fe);
  color: #fff;
  font-size: 30px;
  font-weight: 800;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 12px 30px rgba(0, 242, 254, 0.35);
}

.app-name {
  color: #fff;
  font-size: 26px;
  font-weight: 700;
  margin: 0 0 8px;
  letter-spacing: 2px;
}

.slogan {
  color: rgba(255, 255, 255, 0.75);
  font-size: 14px;
  margin: 0;
  letter-spacing: 1px;
}

.card {
  width: 100%;
  max-width: 400px;
  background: #fff;
  border-radius: 20px;
  padding: 28px 20px 20px;
  box-shadow: 0 16px 48px rgba(0, 0, 0, 0.35);
  box-sizing: border-box;
}

.card :deep(.van-cell-group--inset) {
  margin: 0;
  border-radius: 12px;
}

.actions {
  margin-top: 28px;
  padding: 0 16px;
}

.actions :deep(.van-button) {
  font-weight: 600;
  letter-spacing: 4px;
}

.footer {
  margin-top: 22px;
  text-align: center;
  font-size: 14px;
}

.muted {
  color: #909399;
}

.link {
  color: #1989fa;
  font-weight: 600;
  text-decoration: none;
}
</style>