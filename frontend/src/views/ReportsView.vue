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
const brokenKeyframeUrls = ref(new Set())

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

const selectedStats = computed(() => {
  const alerts = selectedAlerts.value
  const mediumCount = alerts.filter((item) => item.level === 'medium').length
  return {
    total: selectedReport.value?.alertCount ?? alerts.length,
    high: selectedReport.value?.highAlertCount ?? alerts.filter((item) => item.level === 'high').length,
    medium: mediumCount,
    pending: selectedReport.value?.pendingAlertCount ?? alerts.filter((item) => item.status === 'pending').length,
  }
})

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
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  const hour = String(date.getHours()).padStart(2, '0')
  const minute = String(date.getMinutes()).padStart(2, '0')
  const second = String(date.getSeconds()).padStart(2, '0')
  return `${year}-${month}-${day} ${hour}:${minute}:${second}`
}

function formatDisplayTime(value) {
  if (!value) return '-'
  if (/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/.test(value)) return value
  return formatDateTime(value)
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

function keyframeImageUrl(alert) {
  const url = resolveMediaUrl(alert?.keyframeUrl || '')
  return url && !brokenKeyframeUrls.value.has(url) ? url : ''
}

function markKeyframeBroken(alert) {
  const url = resolveMediaUrl(alert?.keyframeUrl || '')
  if (!url) return
  brokenKeyframeUrls.value = new Set([...brokenKeyframeUrls.value, url])
}

async function isDocxBlob(blob) {
  if (!(blob instanceof Blob) || blob.size < 4) return false
  const signature = new Uint8Array(await blob.slice(0, 4).arrayBuffer())
  return signature[0] === 0x50 && signature[1] === 0x4b && signature[2] === 0x03 && signature[3] === 0x04
}

async function blobErrorMessage(blob, fallback) {
  if (!(blob instanceof Blob) || !blob.type.includes('json')) return fallback
  try {
    const payload = JSON.parse(await blob.text())
    return payload?.message || fallback
  } catch (error) {
    return fallback
  }
}

function levelText(level) {
  if (level === 'high') return '高危'
  if (level === 'medium') return '中危'
  if (level === 'low') return '低危'
  return level || '-'
}

function statusText(status) {
  if (status === 'pending') return '待处理'
  if (status === 'processing') return '处理中'
  if (status === 'resolved') return '已处理'
  return status || '-'
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
  brokenKeyframeUrls.value = new Set()
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
    if (!await isDocxBlob(blob)) {
      ElMessage.error(await blobErrorMessage(blob, '报告文件格式异常，请重新生成报告后再下载'))
      return
    }
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `AI告警报告-${row.reportDate}-${(row.periodLabel || 'period').replaceAll(':', '_')}.docx`
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
      <div class="generate-hint">
        不选择时段时，系统会生成最近一个已完整结束的 6 小时时段；同一时段重复生成会更新原报告。
      </div>
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
        description="右侧预览按导出 Word 的章节结构展示：管理建议、统计表、事件明细与关键帧。"
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
          <article class="word-page">
            <header class="word-header">
              <h1>FactoryVision AI 告警时段报告</h1>
              <p>统计周期：{{ formatPeriod(selectedReport.periodStart, selectedReport.periodEnd) }}</p>
              <p>统计时段：{{ selectedReport.periodLabel }}</p>
            </header>

            <section class="word-section">
              <h2>一、AI 管理建议</h2>
              <div class="advice-box">
                {{ selectedReport.aiSummary || '暂无 AI 管理建议。' }}
              </div>
            </section>

            <section class="word-section">
              <h2>二、告警统计</h2>
              <table class="report-stat-table">
                <thead>
                  <tr>
                    <th>总告警</th>
                    <th>高危</th>
                    <th>中危</th>
                    <th>待处理</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td>{{ selectedStats.total }}</td>
                    <td>{{ selectedStats.high }}</td>
                    <td>{{ selectedStats.medium }}</td>
                    <td>{{ selectedStats.pending }}</td>
                  </tr>
                </tbody>
              </table>
            </section>

            <section class="word-section">
              <h2>三、事件明细（按时间降序）</h2>
              <div v-if="selectedAlerts.length" class="word-events">
                <section v-for="(alert, index) in selectedAlerts" :key="alert.id" class="word-event">
                  <div class="word-event-heading">
                    <h3>{{ index + 1 }}. {{ alert.title }}</h3>
                  </div>
                  <dl class="event-definition-list">
                    <div>
                      <dt>时间</dt>
                      <dd>{{ formatDisplayTime(alert.occurredAt) }}</dd>
                    </div>
                    <div>
                      <dt>摄像头</dt>
                      <dd>{{ alert.cameraName || '-' }}</dd>
                    </div>
                    <div>
                      <dt>类型</dt>
                      <dd>{{ alert.eventType || '-' }}</dd>
                    </div>
                    <div>
                      <dt>等级</dt>
                      <dd>{{ levelText(alert.level) }}</dd>
                    </div>
                    <div>
                      <dt>状态</dt>
                      <dd>{{ statusText(alert.status) }}</dd>
                    </div>
                    <div class="full-line">
                      <dt>说明</dt>
                      <dd>{{ alert.description || '无' }}</dd>
                    </div>
                  </dl>
                  <figure v-if="keyframeImageUrl(alert)" class="keyframe-figure">
                    <img :src="keyframeImageUrl(alert)" alt="事件关键帧" @error="markKeyframeBroken(alert)" />
                    <figcaption>事件关键帧</figcaption>
                  </figure>
                  <div v-else class="empty-keyframe">
                    {{ alert.keyframeUrl ? '关键帧无法加载' : '暂无关键帧' }}
                  </div>
                </section>
              </div>
              <el-empty v-else description="该时段无告警事件" />
            </section>
          </article>
        </template>
        <el-empty v-else description="请选择一条报告进行预览" />
      </div>
    </div>
  </div>
</template>

<style scoped>
.reports-workspace {
  display: grid;
  grid-template-columns: minmax(680px, 1.05fr) minmax(520px, 0.95fr);
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

.generate-hint {
  margin: -4px 0 12px;
  color: var(--fv-text-muted);
  font-size: 13px;
  line-height: 1.6;
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
  overflow: auto;
  padding: 22px;
  border: 1px solid var(--fv-border);
  border-radius: 10px;
  background:
    linear-gradient(90deg, rgba(148, 163, 184, 0.06) 1px, transparent 1px),
    linear-gradient(rgba(148, 163, 184, 0.06) 1px, transparent 1px),
    var(--fv-panel-muted);
  background-size: 24px 24px;
}

.word-page {
  width: min(100%, 820px);
  margin: 0 auto;
  padding: 44px 52px;
  min-height: 1040px;
  background: #ffffff;
  color: #111827;
  box-shadow: 0 12px 30px rgba(0, 0, 0, 0.22);
  font-family: "Microsoft YaHei", "PingFang SC", Arial, sans-serif;
}

.word-header {
  text-align: center;
  margin-bottom: 24px;
}

.word-header h1 {
  margin: 0 0 14px;
  color: #111827;
  font-size: 28px;
  line-height: 1.3;
}

.word-header p {
  margin: 4px 0;
  color: #4b5563;
  font-size: 14px;
}

.word-section {
  margin-top: 24px;
}

.word-section h2 {
  margin: 0 0 12px;
  color: #111827;
  font-size: 18px;
  line-height: 1.4;
}

.advice-box {
  padding: 0;
  background: transparent;
  color: #111827;
  line-height: 1.8;
  white-space: pre-wrap;
}

.report-stat-table {
  width: 100%;
  border-collapse: collapse;
  margin-top: 8px;
  font-size: 14px;
}

.report-stat-table th,
.report-stat-table td {
  border: 1px solid #cbd5e1;
  padding: 10px 12px;
  text-align: center;
}

.report-stat-table th {
  background: #ffffff;
  color: #111827;
  font-weight: 700;
}

.word-events {
  display: flex;
  flex-direction: column;
  gap: 22px;
}

.word-event {
  padding-top: 2px;
  break-inside: avoid;
}

.word-event + .word-event {
  border-top: 1px solid #e5e7eb;
  padding-top: 20px;
}

.word-event-heading {
  display: block;
}

.word-event h3 {
  margin: 0 0 10px;
  color: #111827;
  font-size: 16px;
  line-height: 1.5;
}

.event-definition-list {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px 18px;
  margin: 0 0 12px;
  font-size: 14px;
}

.event-definition-list div {
  display: grid;
  grid-template-columns: 54px 1fr;
  gap: 8px;
}

.event-definition-list .full-line {
  grid-column: 1 / -1;
}

.event-definition-list dt {
  color: #64748b;
  font-weight: 700;
}

.event-definition-list dd {
  margin: 0;
  color: #1f2937;
  word-break: break-word;
}

.keyframe-figure {
  margin: 12px 0 0;
}

.keyframe-figure img {
  display: block;
  width: 100%;
  max-height: 360px;
  object-fit: contain;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  background: #f8fafc;
}

.keyframe-figure figcaption {
  margin-top: 6px;
  text-align: center;
  color: #64748b;
  font-size: 12px;
}

.empty-keyframe {
  display: grid;
  place-items: center;
  height: 110px;
  border: 1px dashed #cbd5e1;
  background: #f8fafc;
  color: #64748b;
}

@media (max-width: 1180px) {
  .reports-workspace {
    grid-template-columns: 1fr;
  }

  .word-page {
    padding: 34px 28px;
  }
}
</style>
