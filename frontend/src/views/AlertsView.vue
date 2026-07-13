<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import SectionHeader from '../components/SectionHeader.vue'
import StatusTag from '../components/StatusTag.vue'
import { alertsApi } from '../api/modules'

const drawerVisible = ref(false)
const selectedAlert = ref(null)
const selectedDetail = ref(null)
const loading = ref(false)
const detailLoading = ref(false)
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

const alertTableRows = computed(() => alertRows.value.map(normalizeAlertRow))
const replay = computed(() => selectedDetail.value?.replay || {})
const eventDetail = computed(() => selectedDetail.value?.event || {})

function normalizeAlertRow(alert) {
  return {
    ...alert,
    camera: alert.cameraName || alert.cameraId || '未关联摄像头',
    type: alert.eventType,
    level: alert.severity,
    time: formatDateTime(alert.occurredAt),
  }
}

function formatDateTime(value) {
  if (!value) return '暂无'
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

async function openDetail(row) {
  selectedAlert.value = row
  selectedDetail.value = null
  drawerVisible.value = true
  detailLoading.value = true
  try {
    const response = await alertsApi.detail(row.id)
    selectedDetail.value = response?.data || null
  } catch (error) {
    ElMessage.error(getApiErrorMessage(error, '告警详情加载失败'))
  } finally {
    detailLoading.value = false
  }
}

async function handleAlert(status) {
  if (!selectedAlert.value) return
  handlingStatus.value = status
  try {
    const response = await alertsApi.handle(selectedAlert.value.id, { status })
    const updated = response?.data
    if (updated) {
      alertRows.value = alertRows.value.map((alert) => (alert.id === updated.id ? updated : alert))
      selectedAlert.value = normalizeAlertRow(updated)
      if (selectedDetail.value?.alert) {
        selectedDetail.value.alert = updated
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
      <div class="alert-table-frame">
        <el-table v-loading="loading" :data="alertTableRows" stripe class="stable-alert-table">
          <el-table-column prop="title" label="告警标题" min-width="260" show-overflow-tooltip>
            <template #default="{ row }"><span class="table-cell-ellipsis">{{ row.title }}</span></template>
          </el-table-column>
          <el-table-column prop="camera" label="摄像头" min-width="180" show-overflow-tooltip>
            <template #default="{ row }"><span class="table-cell-ellipsis">{{ row.camera }}</span></template>
          </el-table-column>
          <el-table-column prop="type" label="类型" min-width="170" show-overflow-tooltip>
            <template #default="{ row }"><span class="table-cell-ellipsis">{{ row.type }}</span></template>
          </el-table-column>
          <el-table-column label="等级" width="100"><template #default="{ row }"><StatusTag :value="row.level" /></template></el-table-column>
          <el-table-column label="状态" width="110"><template #default="{ row }"><StatusTag :value="row.status" /></template></el-table-column>
          <el-table-column prop="time" label="时间" min-width="180" />
          <el-table-column label="操作" width="120" fixed="right">
            <template #default="{ row }"><el-button link type="primary" @click="openDetail(row)">查看</el-button></template>
          </el-table-column>
        </el-table>
      </div>
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

    <el-drawer v-model="drawerVisible" title="告警详情" size="520px">
      <template v-if="selectedAlert">
        <el-skeleton v-if="detailLoading" :rows="8" animated />
        <template v-else>
          <el-descriptions :column="1" border>
            <el-descriptions-item label="标题">{{ selectedAlert.title }}</el-descriptions-item>
            <el-descriptions-item label="摄像头">{{ selectedAlert.camera }}</el-descriptions-item>
            <el-descriptions-item label="类型">{{ selectedAlert.type }}</el-descriptions-item>
            <el-descriptions-item label="等级"><StatusTag :value="selectedAlert.level" /></el-descriptions-item>
            <el-descriptions-item label="状态"><StatusTag :value="selectedAlert.status" /></el-descriptions-item>
            <el-descriptions-item label="时间">{{ selectedAlert.time }}</el-descriptions-item>
            <el-descriptions-item label="说明">{{ selectedAlert.description || '暂无' }}</el-descriptions-item>
            <el-descriptions-item label="Track">{{ eventDetail.trackId || '暂无' }}</el-descriptions-item>
            <el-descriptions-item label="置信度">
              {{ eventDetail.confidence != null ? `${(Number(eventDetail.confidence) * 100).toFixed(1)}%` : '暂无' }}
            </el-descriptions-item>
          </el-descriptions>

          <el-divider content-position="left">媒体证据</el-divider>
          <div v-if="replay.media?.keyframeUrl || replay.media?.clipUrl" class="media-preview">
            <img
              v-if="replay.media?.keyframeUrl"
              class="media-preview__image"
              :src="replay.media.keyframeUrl"
              alt="事件关键帧"
            />
            <video
              v-if="replay.media?.clipUrl"
              class="media-preview__video"
              :src="replay.media.clipUrl"
              controls
              muted
              playsinline
            />
          </div>
          <el-descriptions :column="1" border>
            <el-descriptions-item label="关键帧">
              {{ replay.media?.keyframeUrl || replay.media?.keyframePath || '暂无' }}
            </el-descriptions-item>
            <el-descriptions-item label="短视频">
              {{ replay.media?.clipUrl || replay.media?.clipPath || '第二阶段接入' }}
            </el-descriptions-item>
          </el-descriptions>

          <el-divider content-position="left">事件日志</el-divider>
          <pre class="payload-log">{{ JSON.stringify(eventDetail.payload || {}, null, 2) }}</pre>

          <div class="drawer-actions">
            <el-button type="primary" plain :loading="handlingStatus === 'pending'" @click="handleAlert('pending')">确认</el-button>
            <el-button type="warning" plain :loading="handlingStatus === 'processing'" @click="handleAlert('processing')">处理中</el-button>
            <el-button type="danger" plain :loading="handlingStatus === 'closed'" @click="handleAlert('closed')">关闭</el-button>
          </div>
        </template>
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

.alert-table-frame {
  width: 100%;
  max-width: 100%;
  min-width: 0;
  overflow-x: auto;
  overflow-y: hidden;
}

.stable-alert-table {
  width: 100%;
  min-width: 1120px;
}

.stable-alert-table :deep(.el-table__inner-wrapper),
.stable-alert-table :deep(.el-table__header-wrapper),
.stable-alert-table :deep(.el-table__body-wrapper) {
  width: 100%;
  max-width: 100%;
}

.stable-alert-table :deep(.el-table__body-wrapper) {
  max-height: clamp(320px, calc(100vh - 360px), 620px);
  overflow-y: auto;
}

.table-cell-ellipsis {
  display: block;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.payload-log {
  max-height: 220px;
  overflow: auto;
  padding: 12px;
  border-radius: 10px;
  background: #0f172a;
  color: #dbeafe;
  font-size: 12px;
  line-height: 1.6;
}

.media-preview {
  display: grid;
  gap: 12px;
  margin-bottom: 12px;
}

.media-preview__image,
.media-preview__video {
  width: 100%;
  max-height: 280px;
  object-fit: contain;
  border-radius: 12px;
  background: #0f172a;
}
</style>
