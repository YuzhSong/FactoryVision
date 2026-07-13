<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import SectionHeader from '../components/SectionHeader.vue'
import StatusTag from '../components/StatusTag.vue'
import { alertsApi } from '../api/modules'

const drawerVisible = ref(false)
const selectedAlert = ref(null)
const loading = ref(false)
const handlingStatus = ref('')
const alertRows = ref([])
const alertTotal = ref(0)
const filters = reactive({
  keyword: '',
  severity: '',
  status: '',
  alertDate: '',
  page: 1,
  pageSize: 20,
})

const alertTableRows = computed(() => alertRows.value.map((alert) => ({
  ...alert,
  camera: alert.cameraName || alert.cameraId || '未关联摄像头',
  type: alert.eventType,
  level: alert.severity,
  time: formatDateTime(alert.occurredAt),
})))

function formatDateTime(value) {
  if (!value) return '无'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString('zh-CN', { hour12: false })
}

function getApiErrorMessage(error, fallback) {
  const response = error?.response?.data
  if (!response) return fallback
  if (response.message && response.message !== '请求参数错误') return response.message
  if (response.data && typeof response.data === 'object') {
    return Object.entries(response.data)
      .map(([field, messages]) => `${field}: ${Array.isArray(messages) ? messages.join('；') : messages}`)
      .join('；')
  }
  return response.message || fallback
}

function getSelectedDayRange(value) {
  if (!value) return {}
  const start = new Date(`${value}T00:00:00`)
  const end = new Date(`${value}T23:59:59.999`)
  if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime())) return {}
  return {
    startTime: start.toISOString(),
    endTime: end.toISOString(),
  }
}

async function loadAlerts() {
  loading.value = true
  try {
    const timeRange = getSelectedDayRange(filters.alertDate)
    const response = await alertsApi.list({
      keyword: filters.keyword || undefined,
      severity: filters.severity || undefined,
      status: filters.status || undefined,
      startTime: timeRange.startTime,
      endTime: timeRange.endTime,
      page: filters.page,
      pageSize: filters.pageSize,
    })
    alertRows.value = response?.data?.items || []
    alertTotal.value = response?.data?.total || 0
  } catch (error) {
    alertRows.value = []
    alertTotal.value = 0
    ElMessage.error(getApiErrorMessage(error, '告警列表加载失败'))
  } finally {
    loading.value = false
  }
}

function queryAlerts() {
  filters.page = 1
  loadAlerts()
}

function openDetail(row) {
  selectedAlert.value = row
  drawerVisible.value = true
}

async function handleAlert(status) {
  if (!selectedAlert.value) return
  handlingStatus.value = status
  try {
    const response = await alertsApi.handle(selectedAlert.value.id, { status })
    const updated = response?.data
    if (updated) {
      alertRows.value = alertRows.value.map((alert) => (alert.id === updated.id ? updated : alert))
      selectedAlert.value = {
        ...updated,
        camera: updated.cameraName || updated.cameraId || '未关联摄像头',
        type: updated.eventType,
        level: updated.severity,
        time: formatDateTime(updated.occurredAt),
      }
    }
    ElMessage.success('告警状态已更新')
  } catch (error) {
    ElMessage.error(getApiErrorMessage(error, '告警处置失败'))
  } finally {
    handlingStatus.value = ''
  }
}

onMounted(() => {
  loadAlerts()
})
</script>

<template>
  <div class="page-grid">
    <div class="panel table-panel">
      <SectionHeader title="告警中心" />
      <div class="filter-row">
        <el-input v-model="filters.keyword" placeholder="关键词" clearable @keyup.enter="queryAlerts" />
        <el-select v-model="filters.severity" placeholder="等级" clearable>
          <el-option label="高危" value="high" />
          <el-option label="中危" value="medium" />
          <el-option label="低危" value="low" />
          <el-option label="信息" value="info" />
        </el-select>
        <el-select v-model="filters.status" placeholder="状态" clearable>
          <el-option label="待处理" value="pending" />
          <el-option label="处理中" value="processing" />
          <el-option label="已关闭" value="closed" />
        </el-select>
        <el-date-picker v-model="filters.alertDate" type="date" value-format="YYYY-MM-DD" placeholder="选择日期" clearable />
        <el-button type="primary" @click="queryAlerts">查询</el-button>
      </div>
      <el-table v-loading="loading" :data="alertTableRows" stripe class="stable-alert-table" table-layout="fixed">
        <el-table-column prop="title" label="告警标题" width="260" show-overflow-tooltip>
          <template #default="{ row }"><span class="table-cell-ellipsis">{{ row.title }}</span></template>
        </el-table-column>
        <el-table-column prop="camera" label="摄像头" width="160" show-overflow-tooltip>
          <template #default="{ row }"><span class="table-cell-ellipsis">{{ row.camera }}</span></template>
        </el-table-column>
        <el-table-column prop="type" label="类型" width="150" show-overflow-tooltip>
          <template #default="{ row }"><span class="table-cell-ellipsis">{{ row.type }}</span></template>
        </el-table-column>
        <el-table-column label="等级" width="100"><template #default="{ row }"><StatusTag :value="row.level" /></template></el-table-column>
        <el-table-column label="状态" width="110"><template #default="{ row }"><StatusTag :value="row.status" /></template></el-table-column>
        <el-table-column prop="time" label="时间" width="180" />
        <el-table-column label="操作" width="120">
          <template #default="{ row }"><el-button link type="primary" @click="openDetail(row)">查看</el-button></template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!loading && alertTableRows.length === 0" description="暂无告警数据" />
      <el-pagination
        v-model:current-page="filters.page"
        v-model:page-size="filters.pageSize"
        class="pagination"
        layout="total, prev, pager, next"
        :total="alertTotal"
        @current-change="loadAlerts"
      />
    </div>

    <el-drawer v-model="drawerVisible" title="告警详情" size="420px">
      <template v-if="selectedAlert">
        <el-descriptions :column="1" border>
          <el-descriptions-item label="标题">{{ selectedAlert.title }}</el-descriptions-item>
          <el-descriptions-item label="摄像头">{{ selectedAlert.camera }}</el-descriptions-item>
          <el-descriptions-item label="类型">{{ selectedAlert.type }}</el-descriptions-item>
          <el-descriptions-item label="等级"><StatusTag :value="selectedAlert.level" /></el-descriptions-item>
          <el-descriptions-item label="状态"><StatusTag :value="selectedAlert.status" /></el-descriptions-item>
          <el-descriptions-item label="时间">{{ selectedAlert.time }}</el-descriptions-item>
          <el-descriptions-item label="说明">{{ selectedAlert.description || '无' }}</el-descriptions-item>
        </el-descriptions>
        <el-divider />
        <div class="drawer-actions">
          <el-button type="primary" plain :loading="handlingStatus === 'pending'" @click="handleAlert('pending')">确认</el-button>
          <el-button type="warning" plain :loading="handlingStatus === 'processing'" @click="handleAlert('processing')">处理中</el-button>
          <el-button type="danger" plain :loading="handlingStatus === 'closed'" @click="handleAlert('closed')">关闭</el-button>
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

.stable-alert-table {
  width: 100%;
}

.stable-alert-table :deep(.el-table__inner-wrapper),
.stable-alert-table :deep(.el-table__header-wrapper),
.stable-alert-table :deep(.el-table__body-wrapper) {
  width: 100%;
  max-width: 100%;
}

.table-cell-ellipsis {
  display: block;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
