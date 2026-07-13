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
const replayGeometry = computed(() => buildReplayGeometry(replay.value))

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

function buildReplayGeometry(replayData) {
  const trajectory = Array.isArray(replayData?.trajectory) ? replayData.trajectory : []
  const regionPoints = Array.isArray(replayData?.region?.points) ? replayData.region.points : []
  const triggerPoint = normalizePoint(replayData?.triggerPoint)
  const allPoints = [
    ...trajectory.map((item) => normalizePoint(item.center)).filter(Boolean),
    ...trajectory.flatMap((item) => bboxToPoints(item.bbox)),
    ...regionPoints.map(normalizePoint).filter(Boolean),
    triggerPoint,
  ].filter(Boolean)

  if (!allPoints.length) {
    return { hasEvidence: false, path: '', region: '', trigger: null, boxes: [] }
  }

  const bounds = allPoints.reduce(
    (acc, point) => ({
      minX: Math.min(acc.minX, point[0]),
      minY: Math.min(acc.minY, point[1]),
      maxX: Math.max(acc.maxX, point[0]),
      maxY: Math.max(acc.maxY, point[1]),
    }),
    { minX: Infinity, minY: Infinity, maxX: -Infinity, maxY: -Infinity },
  )
  const width = Math.max(1, bounds.maxX - bounds.minX)
  const height = Math.max(1, bounds.maxY - bounds.minY)
  const pad = 10
  const scalePoint = (point) => {
    const x = pad + ((point[0] - bounds.minX) / width) * (100 - pad * 2)
    const y = pad + ((point[1] - bounds.minY) / height) * (100 - pad * 2)
    return [Number(x.toFixed(2)), Number(y.toFixed(2))]
  }
  const path = trajectory
    .map((item) => normalizePoint(item.center))
    .filter(Boolean)
    .map(scalePoint)
    .map((point) => point.join(','))
    .join(' ')
  const region = regionPoints
    .map(normalizePoint)
    .filter(Boolean)
    .map(scalePoint)
    .map((point) => point.join(','))
    .join(' ')
  const boxes = trajectory
    .map((item) => normalizeBbox(item.bbox))
    .filter(Boolean)
    .slice(-3)
    .map((bbox) => {
      const topLeft = scalePoint([bbox[0], bbox[1]])
      const bottomRight = scalePoint([bbox[2], bbox[3]])
      return {
        x: Math.min(topLeft[0], bottomRight[0]),
        y: Math.min(topLeft[1], bottomRight[1]),
        width: Math.abs(bottomRight[0] - topLeft[0]),
        height: Math.abs(bottomRight[1] - topLeft[1]),
      }
    })

  return {
    hasEvidence: true,
    path,
    region,
    trigger: triggerPoint ? scalePoint(triggerPoint) : null,
    boxes,
  }
}

function normalizePoint(point) {
  const value = Array.isArray(point) && point.length >= 2
    ? [Number(point[0]), Number(point[1])]
    : point && typeof point === 'object'
      ? [Number(point.x), Number(point.y)]
      : null
  return value && value.every(Number.isFinite) ? value : null
}

function normalizeBbox(bbox) {
  let value = null
  if (Array.isArray(bbox) && bbox.length >= 4) {
    value = bbox.slice(0, 4).map(Number)
  }
  if (bbox && typeof bbox === 'object') {
    if (['x1', 'y1', 'x2', 'y2'].every((key) => key in bbox)) {
      value = [bbox.x1, bbox.y1, bbox.x2, bbox.y2].map(Number)
    }
    if (['x', 'y', 'w', 'h'].every((key) => key in bbox)) {
      value = [bbox.x, bbox.y, Number(bbox.x) + Number(bbox.w), Number(bbox.y) + Number(bbox.h)].map(Number)
    }
  }
  return value && value.every(Number.isFinite) ? value : null
}

function bboxToPoints(bbox) {
  const normalized = normalizeBbox(bbox)
  if (!normalized) return []
  const [x1, y1, x2, y2] = normalized
  return [[x1, y1], [x2, y2]]
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

          <el-divider content-position="left">事件回放</el-divider>
          <section class="replay-card">
            <div class="replay-card__header">
              <div>
                <p class="replay-title">关键轨迹</p>
                <p class="replay-subtitle">
                  {{ replay.region?.name ? `区域：${replay.region.name}` : '暂无区域名称' }}
                  · {{ replay.trajectory?.length || 0 }} 个轨迹点
                </p>
              </div>
              <el-tag size="small" :type="replayGeometry.hasEvidence ? 'success' : 'info'">
                {{ replayGeometry.hasEvidence ? '已生成' : '无轨迹' }}
              </el-tag>
            </div>
            <svg v-if="replayGeometry.hasEvidence" class="replay-canvas" viewBox="0 0 100 100" role="img">
              <polygon v-if="replayGeometry.region" :points="replayGeometry.region" class="replay-region" />
              <rect
                v-for="(box, index) in replayGeometry.boxes"
                :key="index"
                :x="box.x"
                :y="box.y"
                :width="box.width"
                :height="box.height"
                class="replay-box"
              />
              <polyline v-if="replayGeometry.path" :points="replayGeometry.path" class="replay-path" />
              <circle
                v-if="replayGeometry.trigger"
                :cx="replayGeometry.trigger[0]"
                :cy="replayGeometry.trigger[1]"
                r="3.2"
                class="replay-trigger"
              />
            </svg>
            <el-empty v-else description="这个事件暂时没有可回放轨迹" />
          </section>

          <el-divider content-position="left">媒体证据</el-divider>
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

.replay-card {
  padding: 14px;
  border: 1px solid rgba(148, 163, 184, 0.24);
  border-radius: 14px;
  background: linear-gradient(135deg, rgba(15, 23, 42, 0.03), rgba(59, 130, 246, 0.05));
}

.replay-card__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.replay-title,
.replay-subtitle {
  margin: 0;
}

.replay-title {
  font-weight: 700;
  color: #0f172a;
}

.replay-subtitle {
  margin-top: 4px;
  color: #64748b;
  font-size: 12px;
}

.replay-canvas {
  display: block;
  width: 100%;
  height: 260px;
  border-radius: 12px;
  background:
    linear-gradient(rgba(148, 163, 184, 0.14) 1px, transparent 1px),
    linear-gradient(90deg, rgba(148, 163, 184, 0.14) 1px, transparent 1px),
    #f8fafc;
  background-size: 20px 20px;
}

.replay-region {
  fill: rgba(239, 68, 68, 0.12);
  stroke: rgba(239, 68, 68, 0.75);
  stroke-width: 1.8;
  stroke-dasharray: 4 3;
}

.replay-box {
  fill: rgba(59, 130, 246, 0.08);
  stroke: rgba(37, 99, 235, 0.45);
  stroke-width: 1;
}

.replay-path {
  fill: none;
  stroke: #2563eb;
  stroke-width: 2.5;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.replay-trigger {
  fill: #f97316;
  stroke: #ffffff;
  stroke-width: 1.4;
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
</style>
