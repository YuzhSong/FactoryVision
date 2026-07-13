<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import SectionHeader from '../components/SectionHeader.vue'
import StatusTag from '../components/StatusTag.vue'
import { reportsApi } from '../api/modules'

const loading = ref(false)
const detailLoading = ref(false)
const generating = ref(false)
const downloadingId = ref('')
const reportRows = ref([])
const reportTotal = ref(0)
const selectedReport = ref(null)
const previewContent = ref('')

const filters = reactive({
  reportDate: '',
  page: 1,
  pageSize: 20,
})

const reportTableRows = computed(() => reportRows.value.map((report) => ({
  ...report,
  statusText: report.status === 'generated' ? '已生成' : report.status,
})))

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

function disableFutureDate(date) {
  const today = new Date()
  today.setHours(23, 59, 59, 999)
  return date.getTime() > today.getTime()
}

async function loadReports() {
  loading.value = true
  try {
    const response = await reportsApi.list({
      date: filters.reportDate || undefined,
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
      previewContent.value = ''
    }
  } catch (error) {
    reportRows.value = []
    reportTotal.value = 0
    selectedReport.value = null
    previewContent.value = ''
    ElMessage.error(getApiErrorMessage(error, '监控日报列表加载失败'))
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
    previewContent.value = response?.data?.content || ''
  } catch (error) {
    previewContent.value = ''
    ElMessage.error(getApiErrorMessage(error, '日报预览加载失败'))
  } finally {
    detailLoading.value = false
  }
}

async function downloadReport(row) {
  downloadingId.value = row.id
  try {
    const blob = await reportsApi.download(row.id)
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `AI监控日报-${row.reportDate}.docx`
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(url)
    ElMessage.success('日报已开始下载')
  } catch (error) {
    ElMessage.error(getApiErrorMessage(error, '日报下载失败'))
  } finally {
    downloadingId.value = ''
  }
}

async function generateSelectedReport() {
  generating.value = true
  try {
    const reportDate = filters.reportDate || formatDateForApi()
    const response = await reportsApi.generate({ reportDate })
    ElMessage.success(`${reportDate} 日报生成完成`)
    await loadReports()
    if (response?.data) {
      selectedReport.value = response.data
      previewContent.value = response.data.content || ''
    }
  } catch (error) {
    ElMessage.error(getApiErrorMessage(error, '日报生成失败'))
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
      <SectionHeader title="监控日报列表">
        <div class="report-header-actions">
          <el-button :loading="generating" @click="generateSelectedReport">
            生成当日日报
          </el-button>
          <el-button type="primary" :loading="loading" @click="loadReports">刷新</el-button>
        </div>
      </SectionHeader>
      <div class="filter-row">
        <el-date-picker
          v-model="filters.reportDate"
          type="date"
          value-format="YYYY-MM-DD"
          placeholder="选择日报日期"
          :disabled-date="disableFutureDate"
          clearable
        />
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
        <el-table-column prop="reportDate" label="日报日期" width="120" />
        <el-table-column prop="alertCount" label="告警数" width="90" />
        <el-table-column prop="pendingAlertCount" label="待处理" width="90" />
        <el-table-column label="高危" width="80">
          <template #default="{ row }">
            <StatusTag :value="row.highAlertCount > 0 ? 'high' : 'low'" />
          </template>
        </el-table-column>
        <el-table-column prop="aiSummary" label="AI摘要" min-width="260" show-overflow-tooltip />
        <el-table-column prop="statusText" label="状态" width="100" />
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click.stop="previewReport(row)">预览</el-button>
            <el-button link type="primary" :loading="downloadingId === row.id" @click.stop="downloadReport(row)">
              下载
            </el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!loading && reportTableRows.length === 0" description="暂无监控日报，产生告警事件后会自动聚合" />
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
        :title="selectedReport ? `${selectedReport.reportDate} 日报预览` : '日报预览'"
        description="一天一份，汇总全部摄像头告警"
      >
        <el-button
          :disabled="!selectedReport"
          :loading="selectedReport && downloadingId === selectedReport.id"
          type="primary"
          plain
          @click="downloadReport(selectedReport)"
        >
          下载文档
        </el-button>
      </SectionHeader>

      <div v-loading="detailLoading" class="report-preview">
        <pre v-if="previewContent">{{ previewContent }}</pre>
        <el-empty v-else description="请选择一条日报进行预览" />
      </div>
    </div>
  </div>
</template>

<style scoped>
.reports-workspace {
  display: grid;
  grid-template-columns: minmax(640px, 1.1fr) minmax(360px, 0.9fr);
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

.report-preview pre {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  color: var(--fv-text);
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 13px;
  line-height: 1.8;
}

@media (max-width: 1180px) {
  .reports-workspace {
    grid-template-columns: 1fr;
  }
}
</style>
