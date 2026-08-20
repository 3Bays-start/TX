<template>
  <div class="page">
    <van-nav-bar title="平台公告" />
    <van-cell
      v-for="a in list"
      :key="a.id"
      :title="a.title"
      :label="formatTime(a.published_at)"
      clickable
      @click="show(a)"
    />
    <van-empty v-if="!loading && !list.length" description="暂无公告" />

    <van-popup v-model:show="showPopup" round position="bottom" safe-area-inset-bottom>
      <div class="popup-title">{{ current?.title }}</div>
      <div class="popup-body">{{ current?.content || '暂无内容' }}</div>
    </van-popup>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { showToast } from 'vant'
import { getAnnouncements } from '../api/notification'
import type { Announcement } from '../api/notification'
import { formatTime } from '../utils/format'

const list = ref<Announcement[]>([])
const loading = ref(false)
const showPopup = ref(false)
const current = ref<Announcement | null>(null)

onMounted(load)

async function load() {
  loading.value = true
  try {
    list.value = await getAnnouncements()
  } catch (err) {
    showToast(err instanceof Error ? err.message : '加载失败')
  } finally {
    loading.value = false
  }
}

function show(a: Announcement) {
  current.value = a
  showPopup.value = true
}
</script>

<style scoped>
.popup-body {
  padding: 0 16px 32px;
  color: #646566;
  font-size: 14px;
  line-height: 1.7;
  white-space: pre-wrap;
}
</style>