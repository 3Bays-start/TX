<template>
  <div class="page">
    <van-nav-bar title="安全设置" />

    <van-form @submit="submitPassword">
      <van-cell-group inset title="修改密码">
        <van-field
          v-model="pw.old_password"
          type="password"
          name="old_password"
          label="原密码"
          placeholder="请输入原密码"
          :rules="[{ required: true, message: '请输入原密码' }]"
        />
        <van-field
          v-model="pw.new_password"
          type="password"
          name="new_password"
          label="新密码"
          placeholder="8-64位字母+数字"
          :rules="[
            { required: true, message: '请输入新密码' },
            { validator: validatePassword, message: '密码需8-64位字母和数字' },
          ]"
        />
        <div class="actions">
          <van-button round block type="primary" native-type="submit" :loading="pwSubmitting">
            确认修改
          </van-button>
        </div>
      </van-cell-group>
    </van-form>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { showToast } from 'vant'
import { changePassword } from '../api/user'

const pw = ref({ old_password: '', new_password: '' })
const pwSubmitting = ref(false)

function validatePassword(value: string): boolean {
  return /^(?=.*[A-Za-z])(?=.*\d)[A-Za-z\d]{8,64}$/.test(value)
}

async function submitPassword() {
  pwSubmitting.value = true
  try {
    await changePassword({ old_password: pw.value.old_password, new_password: pw.value.new_password })
    showToast('修改成功')
    pw.value = { old_password: '', new_password: '' }
  } catch (err) {
    showToast(err instanceof Error ? err.message : '修改失败')
  } finally {
    pwSubmitting.value = false
  }
}
</script>
