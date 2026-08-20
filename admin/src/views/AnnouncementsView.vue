<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import type { FormInstance, FormRules } from 'element-plus'
import { ElMessage } from 'element-plus'
import { createAnnouncement, listAnnouncements } from '@/api/admin'
import type { Announcement } from '@/api/types'
import { formatDateTime, statusText, tagType } from '@/utils/format'

const loading = ref(false)
const items = ref<Announcement[]>([])

async function load() {
  loading.value = true
  try {
    const res = await listAnnouncements()
    items.value = res.items
  } finally {
    loading.value = false
  }
}

const createDialog = reactive({ visible: false })
const formRef = ref<FormInstance>()
const form = reactive({ title: '', content: '', type: 'NOTICE' })
const rules: FormRules = {
  title: [{ required: true, message: '请输入公告标题', trigger: 'blur' }],
}
const submitLoading = ref(false)

function openCreate() {
  form.title = ''
  form.content = ''
  form.type = 'NOTICE'
  createDialog.visible = true
}

async function submit() {
  if (!formRef.value) return
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  submitLoading.value = true
  try {
    await createAnnouncement({ title: form.title, content: form.content, type: form.type })
    ElMessage.success('公告已发布')
    createDialog.visible = false
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
        <el-button type="primary" @click="openCreate">发布公告</el-button>
      </div>

      <el-table v-loading="loading" :data="items" stripe>
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="title" label="标题" min-width="200" show-overflow-tooltip />
        <el-table-column prop="content" label="内容" min-width="260" show-overflow-tooltip />
        <el-table-column label="类型" width="100">
          <template #default="{ row }">
            <el-tag :type="tagType(row.type)" size="small">{{ statusText(row.type) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="tagType(row.status)" size="small">{{ statusText(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="发布时间" width="180">
          <template #default="{ row }">{{ formatDateTime(row.published_at) }}</template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 发布 -->
    <el-dialog v-model="createDialog.visible" title="发布公告" width="560px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="80px">
        <el-form-item label="标题" prop="title">
          <el-input v-model="form.title" maxlength="100" show-word-limit />
        </el-form-item>
        <el-form-item label="类型">
          <el-radio-group v-model="form.type">
            <el-radio value="NOTICE">通知</el-radio>
            <el-radio value="IMPORTANT">重要</el-radio>
            <el-radio value="NORMAL">普通</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="内容">
          <el-input v-model="form.content" type="textarea" :rows="6" placeholder="公告内容（可选）" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createDialog.visible = false">取消</el-button>
        <el-button type="primary" :loading="submitLoading" @click="submit">发布</el-button>
      </template>
    </el-dialog>
  </div>
</template>
