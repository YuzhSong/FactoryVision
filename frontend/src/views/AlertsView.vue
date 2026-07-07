<script setup>
import { ref } from 'vue'
import SectionHeader from '../components/SectionHeader.vue'
import StatusTag from '../components/StatusTag.vue'
import { alerts } from '../data/placeholders'

const drawerVisible = ref(false)
const selectedAlert = ref(null)

function openDetail(row) {
  selectedAlert.value = row
  drawerVisible.value = true
}
</script>

<template>
  <div class="page-grid">
    <div class="panel table-panel">
      <SectionHeader title="告警中心" description="告警列表接口 planned，当前展示筛选、表格和详情抽屉结构。" />
      <div class="filter-row">
        <el-input placeholder="关键词" clearable />
        <el-select placeholder="等级" clearable><el-option label="高危" value="high" /><el-option label="中危" value="medium" /></el-select>
        <el-select placeholder="状态" clearable><el-option label="待处理" value="pending" /><el-option label="处理中" value="processing" /></el-select>
        <el-date-picker type="daterange" start-placeholder="开始日期" end-placeholder="结束日期" />
        <el-button type="primary">查询</el-button>
      </div>
      <el-table :data="alerts" stripe>
        <el-table-column prop="title" label="告警标题" min-width="160" />
        <el-table-column prop="camera" label="摄像头" min-width="140" />
        <el-table-column prop="type" label="类型" min-width="150" />
        <el-table-column label="等级" width="100"><template #default="{ row }"><StatusTag :value="row.level" /></template></el-table-column>
        <el-table-column label="状态" width="110"><template #default="{ row }"><StatusTag :value="row.status" /></template></el-table-column>
        <el-table-column prop="time" label="时间" min-width="170" />
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }"><el-button link type="primary" @click="openDetail(row)">查看</el-button></template>
        </el-table-column>
      </el-table>
      <el-pagination class="pagination" layout="prev, pager, next" :total="alerts.length" />
    </div>

    <el-drawer v-model="drawerVisible" title="告警详情" size="420px">
      <template v-if="selectedAlert">
        <el-descriptions :column="1" border>
          <el-descriptions-item label="标题">{{ selectedAlert.title }}</el-descriptions-item>
          <el-descriptions-item label="摄像头">{{ selectedAlert.camera }}</el-descriptions-item>
          <el-descriptions-item label="类型">{{ selectedAlert.type }}</el-descriptions-item>
          <el-descriptions-item label="时间">{{ selectedAlert.time }}</el-descriptions-item>
        </el-descriptions>
        <el-divider />
        <el-alert title="处置接口 planned，按钮仅保留交互入口。" type="warning" :closable="false" show-icon />
        <div class="drawer-actions">
          <el-button type="primary" plain>确认</el-button>
          <el-button type="warning" plain>处理中</el-button>
          <el-button type="danger" plain>关闭</el-button>
        </div>
      </template>
    </el-drawer>
  </div>
</template>

<style scoped>
.pagination {
  margin-top: 16px;
  justify-content: flex-end;
}

.drawer-actions {
  display: flex;
  gap: 10px;
  margin-top: 16px;
}
</style>
