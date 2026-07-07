<script setup>
import SectionHeader from '../components/SectionHeader.vue'
import StatusTag from '../components/StatusTag.vue'
import { alerts, cameras, attendanceRecords } from '../data/placeholders'

const chartBars = [38, 55, 44, 72, 60, 88, 64, 52, 76, 58, 66, 80]
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

    <div class="panel">
      <SectionHeader title="事件趋势" description="ECharts 接入 planned，当前用工业监控风格占位图表达趋势区域。" />
      <div class="chart-placeholder" aria-label="事件趋势占位图">
        <span v-for="(height, index) in chartBars" :key="index" class="chart-bar" :style="{ height: `${height}%` }" />
      </div>
    </div>

    <div class="panel table-panel">
      <SectionHeader title="近期告警" description="后续由 /api/alerts/list/ 提供数据。" />
      <el-table :data="alerts" stripe>
        <el-table-column prop="title" label="告警标题" min-width="160" />
        <el-table-column prop="camera" label="摄像头" min-width="140" />
        <el-table-column prop="level" label="等级" width="100">
          <template #default="{ row }"><StatusTag :value="row.level" /></template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="110">
          <template #default="{ row }"><StatusTag :value="row.status" /></template>
        </el-table-column>
        <el-table-column prop="time" label="时间" min-width="170" />
      </el-table>
    </div>
  </div>
</template>
