<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()

const menuItems = [
  { path: '/dashboard', label: '首页看板' },
  { path: '/monitor', label: '实时监控' },
  { path: '/alerts', label: '告警中心' },
  { path: '/employees', label: '员工管理' },
  { path: '/cameras', label: '摄像头管理' },
  { path: '/zones', label: '区域配置' },
  { path: '/attendance', label: '考勤统计' },
]

const activeMenu = computed(() => route.path)

function handleSelect(index) {
  router.push(index)
}
</script>

<template>
  <el-container class="app-shell">
    <el-aside width="240px" class="app-sidebar">
      <div class="brand-block">
        <h1>智安工厂</h1>
        <p>Smart Factory Vision</p>
      </div>
      <el-menu :default-active="activeMenu" class="nav-menu" @select="handleSelect">
        <el-menu-item v-for="item in menuItems" :key="item.path" :index="item.path">
          {{ item.label }}
        </el-menu-item>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header class="app-header">
        <div>
          <h2>{{ route.meta.title || '智安工厂实时视频分析监测系统' }}</h2>
          <p>第一阶段项目骨架</p>
        </div>
        <el-button type="primary" plain @click="router.push('/login')">登录页</el-button>
      </el-header>
      <el-main class="app-main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>
