<script setup>
import SectionHeader from '../components/SectionHeader.vue'
import StatusTag from '../components/StatusTag.vue'
import { attendanceRecords } from '../data/placeholders'
</script>

<template>
  <div class="page-grid">
    <div class="metric-grid">
      <div class="metric-card"><p class="metric-label">到岗人数</p><p class="metric-value">--</p><p class="metric-note">数据待接入</p></div>
      <div class="metric-card"><p class="metric-label">离开次数</p><p class="metric-value">--</p><p class="metric-note">离开/返回检测待接入</p></div>
      <div class="metric-card"><p class="metric-label">异常记录</p><p class="metric-value">--</p><p class="metric-note">考勤规则待接入</p></div>
      <div class="metric-card"><p class="metric-label">统计日期</p><p class="metric-value">07</p><p class="metric-note">2026-07</p></div>
    </div>

    <div class="panel table-panel">
      <SectionHeader title="考勤记录" description="考勤数据待接入，当前保留筛选与表格结构。" />
      <div class="filter-row">
        <el-date-picker type="date" placeholder="选择日期" />
        <el-input placeholder="员工姓名 / 工号" clearable />
        <el-select placeholder="状态" clearable>
          <el-option label="正常" value="normal" />
          <el-option label="异常" value="abnormal" />
        </el-select>
        <el-button type="primary">查询</el-button>
      </div>
      <el-table :data="attendanceRecords" stripe>
        <el-table-column prop="employeeNo" label="工号" width="110" />
        <el-table-column prop="name" label="姓名" width="120" />
        <el-table-column prop="department" label="部门" width="130" />
        <el-table-column prop="firstSeenAt" label="首次识别" width="120" />
        <el-table-column prop="lastSeenAt" label="最后识别" width="120" />
        <el-table-column prop="leaveCount" label="离开次数" width="110" />
        <el-table-column label="状态" width="100"><template #default="{ row }"><StatusTag :value="row.status" /></template></el-table-column>
      </el-table>
    </div>
  </div>
</template>
