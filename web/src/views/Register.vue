<template>
  <div class="register-page">
    <div class="hero">
      <div class="logo">LX</div>
      <h1 class="app-name">注册账号</h1>
      <p class="slogan">填写邀请码开启 LX 之旅</p>
    </div>

    <div class="card">
      <van-form @submit="onSubmit">
        <van-cell-group inset>
          <van-field
            v-model="username"
            name="username"
            left-icon="contact-o"
            label="账号"
            placeholder="3-20位字母/数字/下划线"
            clearable
            :rules="[
              { required: true, message: '请输入账号' },
              { validator: validateUsername, message: '账号需3-20位字母/数字/下划线' },
            ]"
          />
          <van-field
            v-model="inviteCode"
            name="invite_code"
            left-icon="medal-o"
            label="邀请码"
            placeholder="请输入邀请码"
            :rules="[{ required: true, message: '请输入邀请码' }]"
          />
          <van-field
            v-model="password"
            type="password"
            name="password"
            left-icon="lock"
            label="密码"
            placeholder="8-64位字母+数字"
            autocomplete="new-password"
            :rules="[
              { required: true, message: '请输入密码' },
              { validator: validatePassword, message: '密码需8-64位且含字母和数字' },
            ]"
          />
          <van-field
            v-model="confirmPassword"
            type="password"
            name="confirm_password"
            left-icon="lock"
            label="确认密码"
            placeholder="请再次输入密码"
            autocomplete="new-password"
            :rules="[
              { required: true, message: '请再次输入密码' },
              { validator: validateConfirm, message: '两次输入的密码不一致' },
            ]"
          />
        </van-cell-group>
        <div class="actions">
          <van-button
            round
            block
            color="linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)"
            native-type="submit"
            :loading="submitting"
          >
            注 册
          </van-button>
        </div>
      </van-form>

      <div class="footer">
        <span class="muted">已有账号？</span>
        <router-link to="/login" class="link">返回登录</router-link>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { showToast } from 'vant'
import { register } from '../api/auth'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const authStore = useAuthStore()

const username = ref('')
const inviteCode = ref('')
const password = ref('')
const confirmPassword = ref('')
const submitting = ref(false)

function validateUsername(value: string): boolean {
  return /^[A-Za-z0-9_]{3,20}$/.test(value)
}

function validatePassword(value: string): boolean {
  return /^(?=.*[A-Za-z])(?=.*\d)[A-Za-z\d]{8,64}$/.test(value)
}

function validateConfirm(value: string): boolean {
  return value === password.value
}

async function onSubmit() {
  submitting.value = true
  try {
    const res = await register({
      username: username.value,
      invite_code: inviteCode.value,
      password: password.value,
    })
    authStore.setToken(res.access_token)
    showToast('注册成功')
    router.push('/home')
  } catch (err) {
    showToast(err instanceof Error ? err.message : '注册失败')
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.register-page {
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
  padding: 8px 0 32px;
}

.logo {
  width: 64px;
  height: 64px;
  margin: 0 auto 14px;
  border-radius: 18px;
  background: linear-gradient(135deg, #4facfe, #00f2fe);
  color: #fff;
  font-size: 26px;
  font-weight: 800;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 12px 30px rgba(0, 242, 254, 0.35);
}

.app-name {
  color: #fff;
  font-size: 22px;
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
  padding: 24px 20px 20px;
  box-shadow: 0 16px 48px rgba(0, 0, 0, 0.35);
  box-sizing: border-box;
}

.card :deep(.van-cell-group--inset) {
  margin: 0;
  border-radius: 12px;
}

.actions {
  margin-top: 24px;
  padding: 0 16px;
}

.actions :deep(.van-button) {
  font-weight: 600;
  letter-spacing: 4px;
}

.footer {
  margin-top: 20px;
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