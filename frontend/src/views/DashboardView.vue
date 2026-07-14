<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { BarChart } from 'echarts/charts'
import { GridComponent, TooltipComponent } from 'echarts/components'
import * as echarts from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import SectionHeader from '../components/SectionHeader.vue'
import StatusTag from '../components/StatusTag.vue'
import { dashboardApi } from '../api/modules'
import { getStoredTheme } from '../utils/theme'

echarts.use([BarChart, GridComponent, TooltipComponent, CanvasRenderer])

const chartRef = ref(null)
const loading = ref(false)
const summary = ref({
  cameraCount: 0,
  onlineCameraCount: 0,
  employeeCount: 0,
  todayEventCount: 0,
  todayAlertCount: 0,
  pendingAlertCount: 0,
  recentAlerts: [],
  eventTrend: [],
})
let chartInstance = null

const recentAlertRows = computed(() => summary.value.recentAlerts.map((alert) => ({
  ...alert,
  level: alert.severity,
  time: formatDateTime(alert.occurredAt),
})))

function formatDateTime(value) {
  if (!value) return '无'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString('zh-CN', { hour12: false })
}

function formatHour(value) {
  if (!value) return '--:--'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', hour12: false })
}

function renderChart() {
  if (!chartRef.value) return
  const isDark = getStoredTheme() === 'dark'
  const axisColor = isDark ? '#8abbe2' : '#64748b'
  const lineColor = isDark ? 'rgba(34, 211, 238, 0.18)' : '#e5edf6'
  const primaryColor = isDark ? '#22d3ee' : '#2563eb'
  const accentColor = isDark ? '#22c55e' : '#f97316'

  if (!chartInstance) {
    chartInstance = echarts.init(chartRef.value)
  }

  chartInstance.setOption({
    color: [primaryColor],
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      backgroundColor: isDark ? '#0a2147' : '#ffffff',
      borderColor: isDark ? 'rgba(34, 211, 238, 0.38)' : '#d8e0ea',
      textStyle: { color: isDark ? '#e0f2fe' : '#172033' },
    },
    grid: {
      top: 24,
      right: 18,
      bottom: 28,
      left: 34,
      containLabel: true,
    },
    xAxis: {
      type: 'category',
      data: summary.value.eventTrend.map((item) => formatHour(item.hour)),
      axisTick: { show: false },
      axisLine: { lineStyle: { color: lineColor } },
      axisLabel: { color: axisColor },
    },
    yAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: lineColor } },
      axisLabel: { color: axisColor },
    },
    series: [
      {
        name: '事件数',
        type: 'bar',
        data: summary.value.eventTrend.map((item, index) => ({
          value: item.count,
          itemStyle: {
            color: index === 5 ? accentColor : primaryColor,
          },
        })),
        barWidth: 22,
        borderRadius: [6, 6, 0, 0],
      },
    ],
  })
}

async function loadSummary() {
  loading.value = true
  try {
    const response = await dashboardApi.summary()
    summary.value = {
      ...summary.value,
      ...(response?.data || {}),
      recentAlerts: response?.data?.recentAlerts || [],
      eventTrend: response?.data?.eventTrend || [],
    }
    await nextTick()
    renderChart()
  } catch (error) {
    ElMessage.error(error?.response?.data?.message || '首页汇总数据加载失败')
  } finally {
    loading.value = false
  }
}

function resizeChart() {
  chartInstance?.resize()
}

function handleThemeChange() {
  renderChart()
}

onMounted(() => {
  loadSummary()
  window.addEventListener('resize', resizeChart)
  window.addEventListener('factory-theme-change', handleThemeChange)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', resizeChart)
  window.removeEventListener('factory-theme-change', handleThemeChange)
  chartInstance?.dispose()
})
</script>

<template>
  <div class="page-grid">
    <div class="metric-grid">
      <div v-loading="loading" class="metric-card">
        <p class="metric-label">今日告警</p>
        <p class="metric-value">{{ summary.todayAlertCount }}</p>
        <p class="metric-note">待处理 {{ summary.pendingAlertCount }} 条</p>
      </div>
      <div v-loading="loading" class="metric-card">
        <p class="metric-label">在线摄像头</p>
        <p class="metric-value">{{ summary.onlineCameraCount }}</p>
        <p class="metric-note">总计 {{ summary.cameraCount }} 个摄像头</p>
      </div>
      <div v-loading="loading" class="metric-card">
        <p class="metric-label">事件记录</p>
        <p class="metric-value">{{ summary.todayEventCount }}</p>
        <p class="metric-note">今日 AI 事件</p>
      </div>
      <div v-loading="loading" class="metric-card">
        <p class="metric-label">员工档案</p>
        <p class="metric-value">{{ summary.employeeCount }}</p>
        <p class="metric-note">后端员工总数</p>
      </div>
    </div>

    <div class="dashboard-main-grid">
      <div class="panel dashboard-chart">
        <SectionHeader title="事件趋势" />
        <div ref="chartRef" class="dashboard-chart__canvas" aria-label="事件趋势图" />
      </div>

      <div class="panel table-panel compact-table">
        <SectionHeader title="近期告警" />
        <el-table v-loading="loading" :data="recentAlertRows" stripe>
          <el-table-column prop="title" label="告警标题" min-width="150" />
          <el-table-column prop="level" label="等级" width="86">
            <template #default="{ row }"><StatusTag :value="row.level" /></template>
          </el-table-column>
          <el-table-column prop="status" label="状态" width="96">
            <template #default="{ row }"><StatusTag :value="row.status" /></template>
          </el-table-column>
          <el-table-column prop="time" label="时间" min-width="150" />
        </el-table>
        <el-empty v-if="!loading && recentAlertRows.length === 0" description="暂无近期告警" />
      </div>
    </div>
  </div>
</template>
