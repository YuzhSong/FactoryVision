<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { BarChart } from 'echarts/charts'
import { GridComponent, TooltipComponent } from 'echarts/components'
import * as echarts from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import SectionHeader from '../components/SectionHeader.vue'
import StatusTag from '../components/StatusTag.vue'
import { alerts, cameras, attendanceRecords } from '../data/placeholders'
import { getStoredTheme } from '../utils/theme'

echarts.use([BarChart, GridComponent, TooltipComponent, CanvasRenderer])

const chartRef = ref(null)
let chartInstance = null

const trendLabels = ['08:00', '09:00', '10:00', '11:00', '12:00', '13:00', '14:00', '15:00']
const trendValues = [12, 18, 15, 27, 22, 31, 24, 28]

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
      data: trendLabels,
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
        data: trendValues.map((value, index) => ({
          value,
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

function resizeChart() {
  chartInstance?.resize()
}

function handleThemeChange() {
  renderChart()
}

onMounted(() => {
  renderChart()
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
      <div class="metric-card">
        <p class="metric-label">今日告警</p>
        <p class="metric-value">{{ alerts.length }}</p>
        <p class="metric-note">告警中心接口 planned</p>
      </div>
      <div class="metric-card">
        <p class="metric-label">在线摄像头</p>
        <p class="metric-value">{{ cameras.filter((item) => item.status === 'online').length }}</p>
        <p class="metric-note">视频流状态待接入</p>
      </div>
      <div class="metric-card">
        <p class="metric-label">事件记录</p>
        <p class="metric-value">128</p>
        <p class="metric-note">示例趋势数据</p>
      </div>
      <div class="metric-card">
        <p class="metric-label">考勤异常</p>
        <p class="metric-value">{{ attendanceRecords.filter((item) => item.status === 'abnormal').length }}</p>
        <p class="metric-note">考勤统计 planned</p>
      </div>
    </div>

    <div class="dashboard-main-grid">
      <div class="panel dashboard-chart">
        <SectionHeader title="事件趋势" description="ECharts placeholder 数据，后续由事件统计接口替换。" />
        <div ref="chartRef" class="dashboard-chart__canvas" aria-label="事件趋势图" />
      </div>

      <div class="panel table-panel compact-table">
        <SectionHeader title="近期告警" description="后续由 /api/alerts/list/ 提供数据。" />
        <el-table :data="alerts" stripe>
          <el-table-column prop="title" label="告警标题" min-width="150" />
          <el-table-column prop="level" label="等级" width="86">
            <template #default="{ row }"><StatusTag :value="row.level" /></template>
          </el-table-column>
          <el-table-column prop="status" label="状态" width="96">
            <template #default="{ row }"><StatusTag :value="row.status" /></template>
          </el-table-column>
          <el-table-column prop="time" label="时间" min-width="150" />
        </el-table>
      </div>
    </div>
  </div>
</template>
