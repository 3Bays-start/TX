<template>
  <div class="page">
    <van-nav-bar title="信用等级" />
    <div v-if="info" class="credit-card">
      <div class="credit-name">{{ info.current.name }}</div>
      <div class="credit-sub">已完成订单 {{ info.completed_order_count }} 笔</div>
      <div class="credit-progress">
        <van-progress
          :percentage="info.progress"
          stroke-width="8"
          color="linear-gradient(90deg, #1989fa, #07c160)"
        />
        <div v-if="info.next" class="credit-next">
          再完成 {{ info.need }} 笔订单升级为「{{ info.next.name }}」
        </div>
        <div v-else class="credit-next">已达到最高信用等级</div>
      </div>
    </div>

    <van-cell-group inset title="等级规则">
      <van-cell
        v-for="(level, i) in info?.levels ?? []"
        :key="level.code"
        :title="level.name"
        :value="level.min_orders === 0 ? '初始等级' : `累计 ${level.min_orders} 笔`"
        :label="level.description"
      >
        <template #icon>
          <span :class="['level-badge', i === currentIndex ? 'level-badge-active' : '']">{{ i + 1 }}</span>
        </template>
      </van-cell>
    </van-cell-group>
    <div v-if="!info" class="credit-empty">
      <van-empty description="暂无信用等级数据" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { showToast } from 'vant'
import { getMyCredit } from '../api/credit'
import type { CreditInfo } from '../api/credit'

const info = ref<CreditInfo | null>(null)
const currentIndex = computed(() => {
  const current = info.value
  if (!current) return -1
  return current.levels.findIndex((l) => l.code === current.current.code)
})

onMounted(async () => {
  try {
    info.value = await getMyCredit()
  } catch (err) {
    showToast(err instanceof Error ? err.message : '加载失败')
  }
})
</script>

<style scoped>
.credit-card {
  margin: 16px;
  padding: 24px 20px;
  border-radius: 12px;
  color: #fff;
  background: linear-gradient(135deg, #1989fa, #07c160);
  text-align: center;
}
.credit-name {
  font-size: 30px;
  font-weight: 600;
}
.credit-sub {
  margin-top: 8px;
  font-size: 14px;
  opacity: 0.9;
}
.credit-progress {
  margin-top: 20px;
  text-align: left;
}
.credit-next {
  margin-top: 10px;
  font-size: 12px;
  opacity: 0.9;
}
.level-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  margin-right: 10px;
  border-radius: 50%;
  color: #999;
  background: #f2f3f5;
  font-size: 12px;
}
.level-badge-active {
  color: #fff;
  background: linear-gradient(135deg, #1989fa, #07c160);
}
</style>