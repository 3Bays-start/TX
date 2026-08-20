<template>
  <div class="page">
    <van-nav-bar title="客服中心">
      <template #right>
        <span class="nav-action" @click="showCreate = true">新建工单</span>
      </template>
    </van-nav-bar>
    <van-cell
      v-for="t in tickets"
      :key="t.id"
      :title="t.title"
      :label="formatTime(t.created_at)"
      is-link
      @click="openDetail(t)"
    >
      <template #value>
        <van-tag :type="statusTagType(t.status)">{{ statusText(t.status) }}</van-tag>
      </template>
    </van-cell>
    <van-empty v-if="!tickets.length" description="暂无工单" />

    <van-popup v-model:show="showCreate" round position="bottom" safe-area-inset-bottom>
      <van-form @submit="submitCreate">
        <div class="popup-title">新建工单</div>
        <van-cell-group inset>
          <van-field
            v-model="createForm.title"
            name="title"
            label="标题"
            placeholder="请输入标题"
            :rules="[{ required: true, message: '请输入标题' }]"
          />
          <van-field v-model="createForm.category" name="category" label="分类" placeholder="选填" />
          <van-field
            v-model="createForm.content"
            name="content"
            label="内容"
            type="textarea"
            rows="3"
            autosize
            placeholder="请描述您的问题"
            :rules="[{ required: true, message: '请输入内容' }]"
          />
        </van-cell-group>
        <div class="popup-actions">
          <van-button round block type="primary" native-type="submit" :loading="creating">
            提交
          </van-button>
        </div>
      </van-form>
    </van-popup>

    <van-popup v-model:show="showDetail" round position="right" :style="{ width: '85%', height: '100%' }">
      <div v-if="current" class="ticket-detail">
        <div class="popup-title">{{ current.title }}</div>
        <div class="ticket-status">
          <van-tag :type="statusTagType(current.status)">{{ statusText(current.status) }}</van-tag>
          <span class="muted">{{ formatTime(current.created_at) }}</span>
        </div>
        <div class="msg-list">
          <div
            v-for="(msg, i) in current.messages"
            :key="i"
            class="msg"
            :class="msg.sender_type === 'USER' ? 'msg-user' : 'msg-support'"
          >
            <div class="msg-sender">{{ msg.sender_type }}</div>
            <div class="msg-content">{{ msg.content }}</div>
            <div class="msg-time">{{ formatTime(msg.created_at) }}</div>
          </div>
          <van-empty v-if="!current.messages?.length" description="暂无消息" />
        </div>
        <div class="reply-box">
          <van-field
            v-model="replyContent"
            type="textarea"
            rows="2"
            autosize
            placeholder="回复客服..."
          />
          <van-button size="small" type="primary" :loading="replying" @click="sendReply">
            发送
          </van-button>
        </div>
      </div>
    </van-popup>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { showToast } from 'vant'
import {
  createTicket,
  getTicket,
  getTickets,
  replyTicket,
} from '../api/support'
import type { Ticket, TicketDetail } from '../api/support'
import { formatTime, statusTagType, statusText } from '../utils/format'

const tickets = ref<Ticket[]>([])
const showCreate = ref(false)
const creating = ref(false)
const createForm = ref({ title: '', category: '', content: '' })
const showDetail = ref(false)
const current = ref<TicketDetail | null>(null)
const replyContent = ref('')
const replying = ref(false)

onMounted(loadTickets)

async function loadTickets() {
  try {
    tickets.value = await getTickets()
  } catch (err) {
    showToast(err instanceof Error ? err.message : '加载失败')
  }
}

async function submitCreate() {
  creating.value = true
  try {
    await createTicket({
      title: createForm.value.title,
      category: createForm.value.category || undefined,
      content: createForm.value.content,
    })
    showToast('提交成功')
    showCreate.value = false
    createForm.value = { title: '', category: '', content: '' }
    loadTickets()
  } catch (err) {
    showToast(err instanceof Error ? err.message : '提交失败')
  } finally {
    creating.value = false
  }
}

async function openDetail(t: Ticket) {
  current.value = t
  showDetail.value = true
  try {
    current.value = await getTicket(t.id)
  } catch (err) {
    showToast(err instanceof Error ? err.message : '加载失败')
  }
}

async function sendReply() {
  const content = replyContent.value.trim()
  if (!content || !current.value) return
  replying.value = true
  try {
    await replyTicket(current.value.id, content)
    replyContent.value = ''
    current.value = await getTicket(current.value.id)
  } catch (err) {
    showToast(err instanceof Error ? err.message : '发送失败')
  } finally {
    replying.value = false
  }
}
</script>

<style scoped>
.ticket-detail {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.ticket-status {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 16px 12px;
}

.msg-list {
  flex: 1;
  overflow-y: auto;
  padding: 0 16px;
}

.msg {
  margin-bottom: 12px;
}

.msg-user {
  text-align: right;
}

.msg-content {
  display: inline-block;
  background: #fff;
  border-radius: 8px;
  padding: 8px 10px;
  margin-top: 4px;
  max-width: 90%;
  word-break: break-all;
}

.msg-sender {
  font-size: 12px;
  color: #969799;
}

.msg-time {
  font-size: 11px;
  color: #c8c9cc;
  margin-top: 2px;
}

.reply-box {
  display: flex;
  align-items: flex-end;
  gap: 8px;
  padding: 12px 16px;
  border-top: 1px solid #ebedf0;
  background: #fff;
}
</style>