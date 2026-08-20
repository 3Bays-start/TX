<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import type { FormInstance, FormRules } from 'element-plus'
import { ElMessage } from 'element-plus'
import { createRole, listPermissions, listRoles, updateRole } from '@/api/admin'
import type { Permission, Role } from '@/api/types'
import { statusText, tagType } from '@/utils/format'

const loading = ref(false)
const items = ref<Role[]>([])
const permissions = ref<Permission[]>([])

const editing = reactive({ visible: false, mode: 'create' as 'create' | 'edit', id: 0 })
const formRef = ref<FormInstance>()
const form = reactive({
  code: '',
  name: '',
  description: '',
  permissionCodes: [] as string[],
})

const rules: FormRules = {
  code: [{ required: true, message: '请输入角色编码', trigger: 'blur' }],
  name: [{ required: true, message: '请输入角色名称', trigger: 'blur' }],
}

const submitLoading = ref(false)

async function load() {
  loading.value = true
  try {
    const [roleRes, permRes] = await Promise.all([listRoles(), listPermissions()])
    items.value = roleRes.items
    permissions.value = permRes.items
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editing.mode = 'create'
  editing.id = 0
  form.code = ''
  form.name = ''
  form.description = ''
  form.permissionCodes = []
  editing.visible = true
}

function openEdit(row: Role) {
  editing.mode = 'edit'
  editing.id = row.id
  form.code = row.code
  form.name = row.name
  form.description = row.description
  form.permissionCodes = [...row.permission_codes]
  editing.visible = true
}

async function submit() {
  if (!formRef.value) return
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  submitLoading.value = true
  try {
    if (editing.mode === 'create') {
      await createRole({
        code: form.code,
        name: form.name,
        description: form.description,
        permission_codes: form.permissionCodes,
      })
      ElMessage.success('角色已创建')
    } else {
      await updateRole(editing.id, {
        name: form.name,
        description: form.description,
        permission_codes: form.permissionCodes,
      })
      ElMessage.success('角色已更新')
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
        <el-button type="primary" @click="openCreate">新增角色</el-button>
      </div>

      <el-table v-loading="loading" :data="items" stripe>
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="code" label="角色编码" width="150" />
        <el-table-column prop="name" label="角色名称" width="150" />
        <el-table-column prop="description" label="描述" min-width="160" show-overflow-tooltip />
        <el-table-column label="系统角色" width="100">
          <template #default="{ row }">
            <el-tag v-if="row.is_system" size="small">系统</el-tag>
            <span v-else class="muted">自定义</span>
          </template>
        </el-table-column>
        <el-table-column label="权限数" width="90">
          <template #default="{ row }">{{ row.permission_codes.length }}</template>
        </el-table-column>
        <el-table-column label="权限列表" min-width="260">
          <template #default="{ row }">
            <el-tag v-for="code in row.permission_codes" :key="code" size="small" class="perm-tag" type="info">
              {{ code }}
            </el-tag>
            <span v-if="row.permission_codes.length === 0" class="muted">无权限</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="90" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 新增/编辑 -->
    <el-dialog
      v-model="editing.visible"
      :title="editing.mode === 'create' ? '新增角色' : '编辑角色'"
      width="560px"
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <el-form-item label="角色编码" prop="code">
          <el-input v-model="form.code" :disabled="editing.mode === 'edit'" placeholder="如 ADMIN_OPERATOR" />
        </el-form-item>
        <el-form-item label="角色名称" prop="name">
          <el-input v-model="form.name" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="2" placeholder="可选" />
        </el-form-item>
        <el-form-item label="权限">
          <el-select
            v-model="form.permissionCodes"
            multiple
            filterable
            placeholder="选择权限点"
            style="width: 100%"
          >
            <el-option
              v-for="p in permissions"
              :key="p.code"
              :label="`${p.name}（${p.code}）`"
              :value="p.code"
            />
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

<style scoped>
.perm-tag {
  margin: 2px 4px 2px 0;
}
</style>
