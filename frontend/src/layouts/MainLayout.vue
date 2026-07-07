<script setup>
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  Bell,
  DataAnalysis,
  Histogram,
  Location,
  Monitor,
  SwitchButton,
  User,
  VideoCamera,
} from '@element-plus/icons-vue'
import { authApi } from '../api/modules'
import { systemStatus } from '../data/placeholders'

const route = useRoute()
const router = useRouter()

const menuItems = [
  { path: '/dashboard', label: '首页看板', icon: DataAnalysis },
  { path: '/monitor', label: '实时监控', icon: Monitor },
  { path: '/alerts', label: '告警中心', icon: Bell },
  { path: '/employees', label: '员工管理', icon: User },
  { path: '/cameras', label: '摄像头管理', icon: VideoCamera },
  { path: '/zones', label: '区域配置', icon: Location },
  { path: '/attendance', label: '考勤统计', icon: Histogram },
]

const activeMenu = computed(() => route.path)
const logoutLoading = ref(false)

function handleSelect(index) {
  router.push(index)
}

async function handleLogout() {
  logoutLoading.value = true
  try {
    await authApi.logout()
    ElMessage.success('已登出')
  } catch (error) {
    ElMessage.warning('已清理本地登录状态')
  } finally {
    localStorage.removeItem('factoryVisionToken')
    localStorage.removeItem('factoryVisionUser')
    logoutLoading.value = false
    router.replace('/login')
  }
}
</script>

<template>
  <el-container class="app-shell">
    <el-aside width="240px" class="app-sidebar">
      <div class="brand-block">
        <div class="brand-mark">FV</div>
        <h1>工厂监测</h1>
        <p>Factory Vision</p>
      </div>
      <el-menu :default-active="activeMenu" class="nav-menu" @select="handleSelect">
        <el-menu-item v-for="item in menuItems" :key="item.path" :index="item.path">
          <el-icon><component :is="item.icon" /></el-icon>
          {{ item.label }}
        </el-menu-item>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header class="app-header">
        <div>
          <h2>{{ route.meta.title || '工厂实时视频分析监测系统' }}</h2>
          <p>工业安全监控工作台 · planned 接口按模块分阶段接入</p>
        </div>
        <div class="status-strip">
          <span v-for="item in systemStatus" :key="item.label" class="status-pill">
            <i class="status-dot" :class="item.type" />
            {{ item.label }}: {{ item.value }}
          </span>
          <el-button :icon="SwitchButton" type="primary" plain :loading="logoutLoading" @click="handleLogout">
            登出
          </el-button>
        </div>
      </el-header>
      <el-main class="app-main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>
