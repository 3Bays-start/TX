<template>
  <div class="page">
    <van-nav-bar title="申诉">
      <template #right>
        <span class="nav-action" @click="showCreate = true">发起申诉</span>
      </template>
    </van-nav-bar>

    <van-cell v-for="a in list" :key="a.id" :title="a.subject" :value="statusText(a.status)" is-link>
      <template #label>
        <div class="appeal-content">{{ a.content }}</div>
        <div class="muted">{{ formatTime(a.created_at) }}</div>
        <div v-if="a.review_reason" class="muted">审核意见：{{ a.review_reason }}</div>
      </template>
    </van-cell>
    <van-empty v-if="finished && !list.length" description="暂无申诉" />
    <div v-if="list.length" class="load-more">
      <van-button v-if="!finished" size="small" plain :loading="loading" @click="loadMore">
        加载更多
      </van-button>
      <span v-else class="finished-text">没有更多了</span>
    </div>

    <van-popup v-model:show="showCreate" round position="bottom" safe-area-inset-bottom>
      <van-form @submit="submitCreate">
        <div class="popup-title">发起申诉</div>
        <van-cell-group inset>
          <van-field v-model="createForm.order_id" name="order_id" label="订单号" type="number" placeholder="选填" />
          <van-field
            v-model="createForm.subject"
            name="subject"
            label="申诉主题"
            placeholder="请输入申诉主题"
            :rules="[{ required: true, message: '请输入申诉主题' }]"
          />
          <van-field
            v-model="createForm.content"
            name="content"
            label="申诉内容"
            type="textarea"
            rows="3"
            autosize
            placeholder="请描述申诉内容"
            :rules="[{ required: true, message: '请输入申诉内容' }]"
          />
          <van-field v-model="createForm.evidence" name="evidence" label="证据" placeholder="选填" />
        </van-cell-group>
        <div class="popup-actions">
          <van-button round block type="primary" native-type="submit" :loading="creating">
            提交
          </van-button>
        </div>
      </van-form>
    </van-popup>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { showToast } from 'vant'
import { createAppeal, getAppeals } from '../api/support'
import type { Appeal } from '../api/support'
import { formatTime, statusText } from '../utils/format'

const list = ref<Appeal[]>([])
const page = ref(1)
const pageSize = 10
const loading = ref(false)
const finished = ref(false)

onMounted(loadMore)
const showCreate = ref(false)
const creating = ref(false)
const createForm = ref({ order_id: '', subject: '', content: '', evidence: '' })

async function loadMore() {
  if (loading.value || finished.value) return
  loading.value = true
  try {
    const res = await getAppeals({ page: page.value, page_size: pageSize })
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

async function submitCreate() {
  creating.value = true
  try {
    await createAppeal({
      order_id: createForm.value.order_id ? Number(createForm.value.order_id) : undefined,
      subject: createForm.value.subject,
      content: createForm.value.content,
      evidence: createForm.value.evidence || undefined,
    })
    showToast('提交成功')
    showCreate.value = false
    createForm.value = { order_id: '', subject: '', content: '', evidence: '' }
    list.value = []
    page.value = 1
    finished.value = false
    loadMore()
  } catch (err) {
    showToast(err instanceof Error ? err.message : '提交失败')
  } finally {
    creating.value = false
  }
}
</script>

<style scoped>
.appeal-content {
  margin: 4px 0;
  word-break: break-all;
}
</style>