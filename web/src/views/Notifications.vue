<template>
  <div class="page">
    <van-nav-bar title="通知中心">
      <template #right>
        <span class="nav-action" @click="readAll">全部已读</span>
      </template>
    </van-nav-bar>
    <van-cell
      v-for="n in list"
      :key="n.id"
      :title="n.title"
      :label="formatTime(n.created_at)"
      :value="n.content"
      clickable
      @click="read(n)"
    >
      <template #icon>
        <van-badge v-if="!n.is_read" dot class="noti-badge">
          <van-icon name="bell-o" />
        </van-badge>
        <van-icon v-else name="bell-o" />
      </template>
    </van-cell>
    <van-empty v-if="finished && !list.length" description="暂无通知" />
    <div v-if="list.length" class="load-more">
      <van-button v-if="!finished" size="small" plain :loading="loading" @click="loadMore">
        加载更多
      </van-button>
      <span v-else class="finished-text">没有更多了</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { showToast } from 'vant'
import {
  getNotifications,
  readAllNotifications,
  readNotification,
} from '../api/notification'
import type { Notification } from '../api/notification'
import { formatTime } from '../utils/format'

const list = ref<Notification[]>([])
const page = ref(1)
const pageSize = 15
const loading = ref(false)
const finished = ref(false)

onMounted(loadMore)

async function loadMore() {
  if (loading.value || finished.value) return
  loading.value = true
  try {
    const res = await getNotifications({ page: page.value, page_size: pageSize })
    const items = res.items ?? []
    list.value.push(...items)
    if (items.length < pageSize || list.value.length >= (res.total ?? Number.MAX_SAFE_INTEGER)) {
      finished.value = true
    } else {
      page.value += 1
    }
  } catch (err) {
    showToast(err instanceof Error ? err.message : '加载失败')
  } finally {
    loading.value = false
  }
}

async function read(n: Notification) {
  if (n.is_read) return
  try {
    await readNotification(n.id)
    n.is_read = true
    showToast('已读')
  } catch (err) {
    showToast(err instanceof Error ? err.message : '操作失败')
  }
}

async function readAll() {
  try {
    const res = await readAllNotifications()
    list.value.forEach((n) => {
      n.is_read = true
    })
    showToast(`已读 ${res.count ?? list.value.length} 条`)
  } catch (err) {
    showToast(err instanceof Error ? err.message : '操作失败')
  }
}
</script>

<style scoped>
.noti-badge {
  margin-right: 10px;
}
</style>