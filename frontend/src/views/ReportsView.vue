<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import SectionHeader from '../components/SectionHeader.vue'
import StatusTag from '../components/StatusTag.vue'
import { reportsApi } from '../api/modules'

const periodOptions = ['00:00-06:00', '06:00-12:00', '12:00-18:00', '18:00-24:00']

const loading = ref(false)
const detailLoading = ref(false)
const generating = ref(false)
const downloadingId = ref('')
const reportRows = ref([])
const reportTotal = ref(0)
const selectedReport = ref(null)

const filters = reactive({
  reportDate: '',
  periodLabel: '',
  page: 1,
  pageSize: 20,
})

const reportTableRows = computed(() => reportRows.value.map((report) => ({
  ...report,
  statusText: report.status === 'generated' ? '已生成' : report.status,
  periodText: report.periodLabel || formatPeriod(report.periodStart, report.periodEnd),
})))

const selectedAlerts = computed(() => selectedReport.value?.alerts || [])

function getApiErrorMessage(error, fallback) {
  const response = error?.response?.data
  if (!response) return fallback
  return response.message || fallback
}

function formatDateForApi(date = new Date()) {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

function formatPeriod(start, end) {
  if (!start || !end) return '-'
  return `${formatDateTime(start)} - ${formatDateTime(end)}`
}

function formatDateTime(value) {
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  const hour = String(date.getHours()).padStart(2, '0')
  const minute = String(date.getMinutes()).padStart(2, '0')
  return `${month}-${day} ${hour}:${minute}`
}

function disableFutureDate(date) {
  const today = new Date()
  today.setHours(23, 59, 59, 999)
  return date.getTime() > today.getTime()
}

function resolveMediaUrl(url) {
  if (!url) return ''
  if (url.startsWith('http://') || url.startsWith('https://')) return url
  if (url.startsWith('/')) return url
  return `/${url}`
}

async function loadReports() {
  loading.value = true
  try {
    const response = await reportsApi.list({
      date: filters.reportDate || undefined,
      periodLabel: filters.periodLabel || undefined,
      page: filters.page,
      pageSize: filters.pageSize,
    })
    reportRows.value = response?.data?.items || []
    reportTotal.value = response?.data?.total || 0

    if (!selectedReport.value && reportRows.value.length > 0) {
      await previewReport(reportRows.value[0])
    }
    if (selectedReport.value && !reportRows.value.some((item) => item.id === selectedReport.value.id)) {
      selectedReport.value = null
    }
  } catch (error) {
    reportRows.value = []
    reportTotal.value = 0
    selectedReport.value = null
    ElMessage.error(getApiErrorMessage(error, '监控报告列表加载失败'))
  } finally {
    loading.value = false
  }
}

function queryReports() {
  filters.page = 1
  loadReports()
}

async function previewReport(row) {
  detailLoading.value = true
  selectedReport.value = row
  try {
    const response = await reportsApi.detail(row.id)
    selectedReport.value = response?.data || row
  } catch (error) {
    ElMessage.error(getApiErrorMessage(error, '报告预览加载失败'))
  } finally {
    detailLoading.value = false
  }
}

async function downloadReport(row) {
  if (!row) return
  downloadingId.value = row.id
  try {
    const blob = await reportsApi.download(row.id)
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `AI告警报告-${row.reportDate}-${row.periodLabel || 'period'}.docx`
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(url)
    ElMessage.success('报告已开始下载')
  } catch (error) {
    ElMessage.error(getApiErrorMessage(error, '报告下载失败'))
  } finally {
    downloadingId.value = ''
  }
}

async function generateSelectedReport() {
  generating.value = true
  try {
    const reportDate = filters.reportDate || formatDateForApi()
    const payload = { reportDate }
    if (filters.periodLabel) payload.periodLabel = filters.periodLabel
    const response = await reportsApi.generate(payload)
    ElMessage.success(filters.periodLabel ? `${reportDate} ${filters.periodLabel} 报告生成完成` : '最近完成时段报告生成完成')
    await loadReports()
    if (response?.data) {
      selectedReport.value = response.data
    }
  } catch (error) {
    ElMessage.error(getApiErrorMessage(error, '报告生成失败'))
  } finally {
    generating.value = false
  }
}

onMounted(() => {
  loadReports()
})
</script>

<template>
  <div class="reports-workspace">
    <div class="panel table-panel reports-list-panel">
      <SectionHeader title="AI 告警时段报告">
        <div class="report-header-actions">
          <el-button :loading="generating" @click="generateSelectedReport">
            生成报告
          </el-button>
          <el-button type="primary" :loading="loading" @click="loadReports">刷新</el-button>
        </div>
      </SectionHeader>
      <div class="filter-row">
        <el-date-picker
          v-model="filters.reportDate"
          type="date"
          value-format="YYYY-MM-DD"
          placeholder="选择日期"
          :disabled-date="disableFutureDate"
          clearable
        />
        <el-select v-model="filters.periodLabel" placeholder="选择时段" clearable>
          <el-option v-for="period in periodOptions" :key="period" :label="period" :value="period" />
        </el-select>
        <el-button type="primary" @click="queryReports">查询</el-button>
      </div>

      <el-table
        v-loading="loading"
        :data="reportTableRows"
        stripe
        class="reports-table"
        height="100%"
        highlight-current-row
        @row-click="previewReport"
      >
        <el-table-column prop="reportDate" label="日期" width="115" />
        <el-table-column prop="periodText" label="时段" width="125" />
        <el-table-column prop="alertCount" label="告警" width="72" />
        <el-table-column prop="pendingAlertCount" label="待处理" width="82" />
        <el-table-column label="高危" width="76">
          <template #default="{ row }">
            <StatusTag :value="row.highAlertCount > 0 ? 'high' : 'low'" />
          </template>
        </el-table-column>
        <el-table-column prop="aiSummary" label="AI 管理建议" min-width="260" show-overflow-tooltip />
        <el-table-column prop="statusText" label="状态" width="88" />
        <el-table-column label="操作" width="140" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click.stop="previewReport(row)">预览</el-button>
            <el-button link type="primary" :loading="downloadingId === row.id" @click.stop="downloadReport(row)">
              下载
            </el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!loading && reportTableRows.length === 0" description="暂无 AI 告警报告" />
      <el-pagination
        v-model:current-page="filters.page"
        v-model:page-size="filters.pageSize"
        class="pagination"
        layout="total, prev, pager, next"
        :total="reportTotal"
        @current-change="loadReports"
      />
    </div>

    <div class="panel report-preview-panel">
      <SectionHeader
        :title="selectedReport ? `${selectedReport.reportDate} ${selectedReport.periodLabel || ''} 报告预览` : '报告预览'"
        description="每 6 小时自动生成一份，AI 负责生成管理建议，事件明细保留真实关键帧"
      >
        <el-button
          :disabled="!selectedReport"
          :loading="selectedReport && downloadingId === selectedReport.id"
          type="primary"
          plain
          @click="downloadReport(selectedReport)"
        >
          下载 Word
        </el-button>
      </SectionHeader>

      <div v-loading="detailLoading" class="report-preview">
        <template v-if="selectedReport">
          <div class="summary-card">
            <div class="summary-eyebrow">AI 管理建议</div>
            <p>{{ selectedReport.aiSummary || '暂无 AI 管理建议' }}</p>
          </div>

          <div class="report-meta">
            <span>统计周期：{{ formatPeriod(selectedReport.periodStart, selectedReport.periodEnd) }}</span>
            <span>告警数：{{ selectedReport.alertCount }}</span>
            <span>高危：{{ selectedReport.highAlertCount }}</span>
            <span>待处理：{{ selectedReport.pendingAlertCount }}</span>
          </div>

          <div class="event-list">
            <div v-for="alert in selectedAlerts" :key="alert.id" class="event-card">
              <div class="event-card-header">
                <div>
                  <h4>{{ alert.title }}</h4>
                  <p>{{ alert.occurredAt }} · {{ alert.cameraName }}</p>
                </div>
                <StatusTag :value="alert.level" />
              </div>
              <div class="event-fields">
                <span>类型：{{ alert.eventType }}</span>
                <span>状态：{{ alert.status }}</span>
              </div>
              <p class="event-desc">{{ alert.description || '暂无说明' }}</p>
              <img
                v-if="alert.keyframeUrl"
                class="event-keyframe"
                :src="resolveMediaUrl(alert.keyframeUrl)"
                alt="事件关键帧"
              />
              <div v-else class="empty-keyframe">暂无关键帧</div>
            </div>
          </div>

          <el-empty v-if="selectedAlerts.length === 0" description="该时段无告警事件" />
        </template>
        <el-empty v-else description="请选择一条报告进行预览" />
      </div>
    </div>
  </div>
</template>

<style scoped>
.reports-workspace {
  display: grid;
  grid-template-columns: minmax(680px, 1.1fr) minmax(420px, 0.9fr);
  gap: 20px;
  align-items: stretch;
}

.report-header-actions {
  display: flex;
  gap: 10px;
}

.reports-list-panel,
.report-preview-panel {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 172px);
  min-height: 560px;
  overflow: hidden;
}

.filter-row {
  display: flex;
  gap: 12px;
  align-items: center;
  margin-bottom: 14px;
}

.reports-table {
  flex: 1;
  min-height: 0;
  width: 100%;
}

.reports-list-panel :deep(.el-table__body-wrapper) {
  max-height: none;
  overflow-y: auto;
}

.pagination {
  margin-top: 16px;
  justify-content: flex-end;
}

.report-preview {
  flex: 1;
  min-height: 0;
  max-height: none;
  overflow: auto;
  padding: 16px;
  border: 1px solid var(--fv-border);
  border-radius: 8px;
  background: var(--fv-panel-muted);
}

.summary-card {
  padding: 16px;
  border-radius: 12px;
  border: 1px solid rgba(34, 211, 238, 0.25);
  background: rgba(34, 211, 238, 0.08);
  margin-bottom: 14px;
}

.summary-eyebrow {
  font-size: 12px;
  color: var(--fv-accent);
  margin-bottom: 8px;
}

.summary-card p {
  margin: 0;
  color: var(--fv-text);
  line-height: 1.7;
}

.report-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 14px;
  color: var(--fv-text-muted);
  font-size: 13px;
}

.event-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.event-card {
  padding: 14px;
  border-radius: 12px;
  border: 1px solid var(--fv-border);
  background: var(--fv-panel);
}

.event-card-header {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
}

.event-card h4 {
  margin: 0 0 4px;
  color: var(--fv-text);
}

.event-card p {
  margin: 0;
  color: var(--fv-text-muted);
  line-height: 1.6;
}

.event-fields {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin: 10px 0;
  color: var(--fv-text-muted);
  font-size: 13px;
}

.event-desc {
  margin-bottom: 10px !important;
}

.event-keyframe,
.empty-keyframe {
  width: 100%;
  border-radius: 10px;
  border: 1px solid var(--fv-border);
  background: rgba(255, 255, 255, 0.04);
}

.event-keyframe {
  display: block;
  max-height: 260px;
  object-fit: contain;
}

.empty-keyframe {
  display: grid;
  place-items: center;
  height: 120px;
  color: var(--fv-text-muted);
}

@media (max-width: 1180px) {
  .reports-workspace {
    grid-template-columns: 1fr;
  }
}
</style>
