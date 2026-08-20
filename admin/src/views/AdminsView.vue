<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import type { FormInstance, FormRules } from 'element-plus'
import { ElMessage } from 'element-plus'
import { createAdmin, listAdmins, listRoles, updateAdmin } from '@/api/admin'
import type { AdminUser, Role } from '@/api/types'
import { formatDateTime, statusText, tagType } from '@/utils/format'

const loading = ref(false)
const items = ref<AdminUser[]>([])
const roles = ref<Role[]>([])
const editing = reactive({ visible: false, mode: 'create' as 'create' | 'edit', id: 0 })

const formRef = ref<FormInstance>()
const form = reactive({
  username: '',
  password: '',
  nickname: '',
  status: 'ACTIVE',
  roleIds: [] as number[],
})

const rules: FormRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 50, message: '长度 3-50 个字符', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 8, max: 64, message: '长度 8-64 个字符', trigger: 'blur' },
  ],
}

const submitLoading = ref(false)

async function load() {
  loading.value = true
  try {
    const [adminRes, roleRes] = await Promise.all([listAdmins(), listRoles()])
    items.value = adminRes.items
    roles.value = roleRes.items
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editing.mode = 'create'
  editing.id = 0
  form.username = ''
  form.password = ''
  form.nickname = ''
  form.status = 'ACTIVE'
  form.roleIds = []
  editing.visible = true
}

function openEdit(row: AdminUser) {
  editing.mode = 'edit'
  editing.id = row.id
  form.username = row.username
  form.password = ''
  form.nickname = row.nickname
  form.status = row.status
  form.roleIds = []
  editing.visible = true
}

async function submit() {
  if (!formRef.value) return
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  submitLoading.value = true
  try {
    if (editing.mode === 'create') {
      await createAdmin({
        username: form.username,
        password: form.password,
        nickname: form.nickname,
        role_ids: form.roleIds,
      })
      ElMessage.success('管理员已创建')
    } else {
      const payload: { nickname?: string; password?: string; status?: string; role_ids?: number[] } = {
        nickname: form.nickname,
        status: form.status,
        role_ids: form.roleIds,
      }
      if (form.password) payload.password = form.password
      await updateAdmin(editing.id, payload)
      ElMessage.success('管理员已更新')
    }
    editing.visible = false
    load()
  } finally {
    submitLoading.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="page">
    <el-card shadow="never">
      <div class="toolbar">
        <el-button type="primary" @click="openCreate">新增管理员</el-button>
      </div>

      <el-table v-loading="loading" :data="items" stripe>
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="username" label="用户名" width="150" />
        <el-table-column prop="nickname" label="昵称" min-width="140" show-overflow-tooltip />
        <el-table-column prop="role_code" label="角色编码" width="150" />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="tagType(row.status)" size="small">{{ statusText(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="超管" width="90">
          <template #default="{ row }">
            <el-tag v-if="row.is_super" type="warning" size="small" effect="dark">超管</el-tag>
            <span v-else class="muted">-</span>
          </template>
        </el-table-column>
        <el-table-column label="最近登录" width="170">
          <template #default="{ row }">{{ formatDateTime(row.last_login_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="100" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 新增/编辑 -->
    <el-dialog
      v-model="editing.visible"
      :title="editing.mode === 'create' ? '新增管理员' : '编辑管理员'"
      width="520px"
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-width="90px">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="form.username" :disabled="editing.mode === 'edit'" placeholder="3-50 个字符" />
        </el-form-item>
        <el-form-item label="密码" :prop="editing.mode === 'create' ? 'password' : undefined">
          <el-input
            v-model="form.password"
            type="password"
            show-password
            :placeholder="editing.mode === 'edit' ? '留空则不修改' : '至少 8 个字符'"
          />
        </el-form-item>
        <el-form-item label="昵称">
          <el-input v-model="form.nickname" placeholder="可选" />
        </el-form-item>
        <el-form-item label="状态" v-if="editing.mode === 'edit'">
          <el-radio-group v-model="form.status">
            <el-radio value="ACTIVE">正常</el-radio>
            <el-radio value="DISABLED">禁用</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="角色">
          <el-select v-model="form.roleIds" multiple placeholder="选择角色" style="width: 100%">
            <el-option v-for="r in roles" :key="r.id" :label="r.name" :value="r.id" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editing.visible = false">取消</el-button>
        <el-button type="primary" :loading="submitLoading" @click="submit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>
