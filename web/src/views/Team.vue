<template>
  <div class="page">
    <van-nav-bar title="我的团队" />
    <van-cell-group inset title="团队概况">
      <van-cell title="总人数" :value="String(summary.total_team ?? '-')" />
      <van-cell title="直接成员" :value="String(summary.direct_count ?? '-')" />
      <van-cell title="活跃人数" :value="String(summary.active_count ?? '-')" />
      <van-cell title="团队订单" :value="`${summary.team_order_count ?? 0} 笔`" />
      <van-cell title="团队成交额" :value="formatMoney(summary.team_order_amount)" />
    </van-cell-group>

    <van-cell-group inset title="我的邀请码（唯一）">
      <van-cell
        v-for="c in codes"
        :key="c.id"
        :title="c.code"
        :label="`状态：${statusText(c.status)}`"
      >
        <template #value>
          <van-button size="mini" type="primary" plain @click="copyCode(c.code)">复制</van-button>
        </template>
      </van-cell>
      <van-empty v-if="!codes.length" description="暂无邀请码" />
    </van-cell-group>

    <van-cell-group inset title="可切换登录的账号">
      <van-cell
        v-for="s in switchable"
        :key="s.user_id"
        :title="s.nickname || s.username"
        :label="`账号：${s.username}`"
      >
        <template #value>
          <van-button size="mini" type="success" plain @click="switchTo(s)">切换登录</van-button>
        </template>
      </van-cell>
      <van-empty v-if="!switchable.length" description="暂无，邀请好友注册后可切换登录其账号" />
    </van-cell-group>

    <van-cell-group inset title="团队成员">
      <van-cell
        v-for="m in members"
        :key="m.user_id"
        :title="m.nickname || m.username"
        :label="m.username"
        :value="formatTime(m.created_at)"
      />
      <van-empty v-if="!members.length" description="暂无成员" />
    </van-cell-group>
    <div v-if="members.length" class="load-more">
      <van-button v-if="!membersFinished" size="small" plain :loading="membersLoading" @click="loadMembers">
        加载更多
      </van-button>
      <span v-else class="finished-text">没有更多了</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { showToast } from 'vant'
import { getSwitchable, getTeam, getTeamSummary } from '../api/user'
import type { SwitchableMember, TeamMember, TeamSummary } from '../api/user'
import { getCodes } from '../api/invite'
import type { InviteCode } from '../api/invite'
import { switchUser } from '../api/auth'
import { useAuthStore } from '../stores/auth'
import { formatMoney, formatTime, statusText } from '../utils/format'

const router = useRouter()
const authStore = useAuthStore()

const summary = ref<TeamSummary>({})
const members = ref<TeamMember[]>([])
const membersPage = ref(1)
const membersLoading = ref(false)
const membersFinished = ref(false)
const codes = ref<InviteCode[]>([])
const switchable = ref<SwitchableMember[]>([])

onMounted(() => {
  loadSummary()
  loadMembers()
  loadCodes()
  loadSwitchable()
})

async function loadSummary() {
  try {
    summary.value = await getTeamSummary()
  } catch (err) {
    showToast(err instanceof Error ? err.message : '加载失败')
  }
}

async function loadMembers() {
  if (membersLoading.value || membersFinished.value) return
  membersLoading.value = true
  try {
    const res = await getTeam({ page: membersPage.value, page_size: 10 })
    const items = res.items ?? []
    members.value.push(...items)
    if (items.length < 10 || members.value.length >= (res.total ?? Number.MAX_SAFE_INTEGER)) {
      membersFinished.value = true
    } else {
      membersPage.value += 1
    }
  } catch (err) {
    showToast(err instanceof Error ? err.message : '加载失败')
  } finally {
    membersLoading.value = false
  }
}

async function loadCodes() {
  try {
    codes.value = await getCodes()
  } catch {
    codes.value = []
  }
}

async function loadSwitchable() {
  try {
    switchable.value = await getSwitchable()
  } catch {
    switchable.value = []
  }
}

async function switchTo(s: SwitchableMember) {
  try {
    const current = localStorage.getItem('lx_token')
    if (current && !localStorage.getItem('lx_switch_from')) {
      localStorage.setItem('lx_switch_from', current)
    }
    const res = await switchUser(s.user_id)
    authStore.setToken(res.access_token)
    showToast(`已切换到 ${s.username} 的账号`)
    router.push('/home')
  } catch (err) {
    showToast(err instanceof Error ? err.message : '切换失败')
  }
}

function copyCode(code: string) {
  if (navigator.clipboard?.writeText) {
    navigator.clipboard
      .writeText(code)
      .then(() => showToast('已复制'))
      .catch(() => showToast('复制失败'))
  } else {
    showToast('复制失败')
  }
}
</script>