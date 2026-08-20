<template>
  <div class="app-container">
    <router-view />
    <van-tabbar v-if="showTabbar" route>
      <van-tabbar-item replace to="/home" icon="home-o">首页</van-tabbar-item>
      <van-tabbar-item replace to="/team" icon="friends-o">团队</van-tabbar-item>
      <van-tabbar-item replace to="/orders" icon="orders-o">订单</van-tabbar-item>
      <van-tabbar-item replace to="/account" icon="balance-o">账户</van-tabbar-item>
      <van-tabbar-item replace to="/profile" icon="user-o">我的</van-tabbar-item>
    </van-tabbar>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const showTabbar = computed(() => route.meta.tabbar === true)
</script>

<style>
html,
body {
  margin: 0;
  padding: 0;
  background: #f7f8fa;
}

.app-container {
  max-width: 480px;
  margin: 0 auto;
  min-height: 100vh;
  position: relative;
}

.app-container .van-tabbar--fixed {
  max-width: 480px;
  left: 50%;
  right: auto;
  transform: translateX(-50%);
}

.page {
  min-height: 100vh;
  box-sizing: border-box;
  padding-bottom: 24px;
}

.section {
  margin: 16px;
}

.section-title {
  font-size: 15px;
  font-weight: 600;
  color: #323233;
  margin-bottom: 10px;
}

.actions {
  margin: 20px 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.load-more {
  text-align: center;
  padding: 12px 0 24px;
}

.finished-text {
  color: #969799;
  font-size: 13px;
}

.muted {
  color: #969799;
  font-size: 12px;
}

.nav-action {
  color: #1989fa;
  font-size: 14px;
  cursor: pointer;
}

.popup-title {
  padding: 16px;
  font-size: 16px;
  font-weight: 600;
  text-align: center;
}

.popup-actions {
  margin: 12px 16px 24px;
}
</style>