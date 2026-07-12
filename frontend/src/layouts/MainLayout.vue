<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  Bell,
  DataAnalysis,
  Histogram,
  Location,
  Moon,
  Monitor,
  Sunny,
  SwitchButton,
  User,
  VideoCamera,
} from '@element-plus/icons-vue'
import { aiServiceApi, authApi, healthApi } from '../api/modules'
import { applyTheme, getStoredTheme } from '../utils/theme'

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
const theme = ref(getStoredTheme())
const isDark = computed(() => theme.value === 'dark')
const backendStatus = ref('checking')
const websocketStatus = ref('idle')
const videoStreamStatus = ref('checking')
let statusTimer = null

const systemStatus = computed(() => [
  {
    label: 'Backend',
    value: backendStatus.value,
    type: backendStatus.value === 'connected' ? 'success' : 'warning',
  },
  {
    label: 'WebSocket',
    value: websocketStatus.value,
    type: websocketStatus.value === 'connected' ? 'success' : 'warning',
  },
  {
    label: 'Video Stream',
    value: videoStreamStatus.value,
    type: videoStreamStatus.value === 'connected' ? 'success' : 'warning',
  },
])

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

function toggleTheme() {
  theme.value = isDark.value ? 'light' : 'dark'
  applyTheme(theme.value)
}

function handleMonitorStatusUpdate(event) {
  const details = Array.isArray(event.detail) ? event.detail : []
  if (details.length === 0) {
    websocketStatus.value = 'idle'
    return
  }

  for (const item of details) {
    if (item?.label === 'WebSocket' && item.value) {
      websocketStatus.value = item.value
    }
    if (item?.label === 'Video Stream' && item.value) {
      videoStreamStatus.value = item.value
    }
  }
}

async function loadSystemStatus() {
  try {
    const response = await healthApi.getHealth()
    const health = response?.data || response
    backendStatus.value = response?.code === 200 || health?.status === 'ok' ? 'connected' : 'warning'
  } catch (error) {
    backendStatus.value = 'offline'
  }

  try {
    const response = await aiServiceApi.streamStatus()
    const streamStatus = response?.data?.data || response?.data || null
    if (streamStatus?.running) {
      videoStreamStatus.value = 'connected'
    } else if (streamStatus?.last_error) {
      videoStreamStatus.value = 'error'
    } else {
      videoStreamStatus.value = 'idle'
    }
  } catch (error) {
    videoStreamStatus.value = 'offline'
  }
}

onMounted(() => {
  loadSystemStatus()
  window.addEventListener('factory-vision-monitor-status', handleMonitorStatusUpdate)
  statusTimer = window.setInterval(loadSystemStatus, 10000)
})

onBeforeUnmount(() => {
  window.removeEventListener('factory-vision-monitor-status', handleMonitorStatusUpdate)
  if (statusTimer) {
    window.clearInterval(statusTimer)
    statusTimer = null
  }
})
</script>

<template>
  <el-container class="app-shell">
    <el-aside width="234px" class="app-sidebar">
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
          <p>工业安全监控工作台</p>
        </div>
        <div class="status-strip">
          <span v-for="item in systemStatus" :key="item.label" class="status-pill">
            <i class="status-dot" :class="item.type" />
            {{ item.label }}: {{ item.value }}
          </span>
          <el-button :icon="isDark ? Sunny : Moon" plain @click="toggleTheme">
            {{ isDark ? '浅色' : '深色' }}
          </el-button>
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
