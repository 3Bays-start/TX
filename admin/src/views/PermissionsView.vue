<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { listPermissions } from '@/api/admin'
import type { Permission } from '@/api/types'

const loading = ref(false)
const items = ref<Permission[]>([])

const groups = computed(() => {
  const map = new Map<string, Permission[]>()
  for (const p of items.value) {
    const key = p.group || '其他'
    const arr = map.get(key) || []
    arr.push(p)
    map.set(key, arr)
  }
  return Array.from(map.entries())
})

async function load() {
  loading.value = true
  try {
    const res = await listPermissions()
    items.value = res.items
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="page">
    <el-alert
      title="只读视图：权限点由系统定义，不可编辑。"
      type="info"
      :closable="false"
      class="readonly-banner"
    />
    <el-card v-for="[group, perms] in groups" :key="group" shadow="never" class="group-card">
      <template #header>
        <span class="group-title">{{ group }}（{{ perms.length }}）</span>
      </template>
      <el-table v-loading="loading" :data="perms" stripe>
        <el-table-column prop="code" label="权限编码" width="220" />
        <el-table-column prop="name" label="权限名称" width="160" />
        <el-table-column prop="description" label="描述" min-width="200" show-overflow-tooltip />
      </el-table>
    </el-card>
  </div>
</template>

<style scoped>
.group-card {
  margin-bottom: 16px;
}

.group-title {
  font-weight: 600;
}
</style>
