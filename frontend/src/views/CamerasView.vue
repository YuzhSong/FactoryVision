<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import SectionHeader from '../components/SectionHeader.vue'
import StatusTag from '../components/StatusTag.vue'
import { camerasApi } from '../api/modules'

const dialogVisible = ref(false)
const loading = ref(false)
const saving = ref(false)
const switchingCameraId = ref(null)
const editingCameraId = ref(null)
const cameraRows = ref([])
const cameraTotal = ref(0)
const filters = reactive({
  keyword: '',
  status: '',
  page: 1,
  pageSize: 20,
})

const cameraForm = reactive({
  name: '',
  code: '',
  location: '',
  streamUrl: '',
  processedStreamUrl: '',
  enabled: true,
  includeFaces: false,
})

const resetCameraForm = () => {
  Object.assign(cameraForm, {
    name: '',
    code: '',
    location: '',
    streamUrl: '',
    processedStreamUrl: '',
    enabled: true,
    includeFaces: false,
  })
}

const openCreateDialog = () => {
  editingCameraId.value = null
  resetCameraForm()
  dialogVisible.value = true
}

const openEditDialog = (row) => {
  editingCameraId.value = row.id
  Object.assign(cameraForm, {
    name: row.name || '',
    code: row.code || '',
    location: row.location || '',
    streamUrl: row.streamUrl || '',
    processedStreamUrl: row.processedStreamUrl || '',
    enabled: row.enabled !== false,
    includeFaces: row.includeFaces === true,
  })
  dialogVisible.value = true
}

const getApiErrorMessage = (error, fallback) => {
  const response = error?.response?.data
  if (!response) return fallback
  if (response.message && response.message !== '请求参数错误') return response.message

  const detail = response.data
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) return detail.join('；')
  if (detail && typeof detail === 'object') {
    return Object.entries(detail)
      .map(([field, messages]) => `${field}: ${Array.isArray(messages) ? messages.join('；') : messages}`)
      .join('；')
  }

  return response.message || fallback
}

const loadCameras = async () => {
  loading.value = true
  try {
    const response = await camerasApi.list({
      keyword: filters.keyword || undefined,
      status: filters.status || undefined,
      page: filters.page,
      pageSize: filters.pageSize,
    })
    cameraRows.value = response?.data?.items || []
    cameraTotal.value = response?.data?.total || 0
  } catch (error) {
    cameraRows.value = []
    cameraTotal.value = 0
    ElMessage.error(getApiErrorMessage(error, '摄像头列表加载失败'))
  } finally {
    loading.value = false
  }
}

const queryCameras = () => {
  filters.page = 1
  loadCameras()
}

const submitCamera = async () => {
  if (!cameraForm.name || !cameraForm.streamUrl) {
    ElMessage.warning('请填写摄像头名称和原始流地址')
    return
  }

  saving.value = true
  try {
    const payload = {
      name: cameraForm.name,
      streamUrl: cameraForm.streamUrl,
      includeFaces: cameraForm.includeFaces,
    }
    if (cameraForm.code) {
      payload.code = cameraForm.code
    }
    if (cameraForm.location) {
      payload.location = cameraForm.location
    }
    if (cameraForm.processedStreamUrl) {
      payload.processedStreamUrl = cameraForm.processedStreamUrl
    }
    if (editingCameraId.value) {
      payload.enabled = cameraForm.enabled
    }

    const response = editingCameraId.value
      ? await camerasApi.update(editingCameraId.value, payload)
      : await camerasApi.create(payload)
    ElMessage.success(editingCameraId.value
      ? `摄像头已更新：${response?.data?.code || cameraForm.code || '当前摄像头'}`
      : `摄像头已创建：${response?.data?.code || '自动编号'}`)
    dialogVisible.value = false
    editingCameraId.value = null
    await loadCameras()
  } catch (error) {
    ElMessage.error(getApiErrorMessage(error, editingCameraId.value ? '摄像头更新失败' : '摄像头创建失败'))
  } finally {
    saving.value = false
  }
}

const toggleCameraStatus = async (row, status) => {
  if (row.status === status) return

  const previousStatus = row.status
  switchingCameraId.value = row.id
  try {
    await camerasApi.toggle(row.id, { status })
    cameraRows.value = cameraRows.value.map((camera) => (
      camera.id === row.id ? { ...camera, status } : camera
    ))
    ElMessage.success('摄像头状态已更新')
    loadCameras()
  } catch (error) {
    cameraRows.value = cameraRows.value.map((camera) => (
      camera.id === row.id ? { ...camera, status: previousStatus } : camera
    ))
    ElMessage.error(getApiErrorMessage(error, '摄像头状态切换失败'))
  } finally {
    switchingCameraId.value = null
  }
}

const deleteCamera = async (row) => {
  try {
    await ElMessageBox.confirm(`确认删除摄像头 ${row.name || row.code}？关联区域也会被删除。`, '删除摄像头', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
    })
  } catch (error) {
    return
  }

  switchingCameraId.value = row.id
  try {
    await camerasApi.remove(row.id)
    ElMessage.success('摄像头已删除')
    await loadCameras()
  } catch (error) {
    ElMessage.error(getApiErrorMessage(error, '摄像头删除失败'))
  } finally {
    switchingCameraId.value = null
  }
}

onMounted(() => {
  loadCameras()
})
</script>

<template>
  <div class="page-grid">
    <div class="panel table-panel">
      <SectionHeader title="摄像头管理">
        <el-button type="primary" @click="openCreateDialog">新增摄像头</el-button>
      </SectionHeader>
      <div class="filter-row">
        <el-input v-model="filters.keyword" placeholder="搜索名称 / 编码 / 位置" clearable @keyup.enter="queryCameras" />
        <el-select v-model="filters.status" placeholder="状态" clearable>
          <el-option label="在线" value="online" />
          <el-option label="离线" value="offline" />
          <el-option label="停用" value="disabled" />
        </el-select>
        <el-button type="primary" @click="queryCameras">查询</el-button>
      </div>
      <el-table v-loading="loading" :data="cameraRows" stripe>
        <el-table-column prop="name" label="摄像头" min-width="150" />
        <el-table-column prop="code" label="编码" width="110" />
        <el-table-column prop="location" label="位置" min-width="130" />
        <el-table-column prop="streamUrl" label="原始流地址" min-width="220" show-overflow-tooltip />
        <el-table-column prop="processedStreamUrl" label="AI处理流地址" min-width="220" show-overflow-tooltip />
        <el-table-column label="状态" width="100"><template #default="{ row }"><StatusTag :value="row.status" /></template></el-table-column>
        <el-table-column label="启用" width="90">
          <template #default="{ row }">
            <span :class="['camera-enabled-text', row.enabled ? 'is-enabled' : 'is-disabled']">
              {{ row.enabled ? '已启用' : '未启用' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="230">
          <template #default="{ row }">
            <div class="camera-actions">
              <el-button link type="primary" @click="openEditDialog(row)">编辑</el-button>
              <el-dropdown
                trigger="click"
                @command="(status) => toggleCameraStatus(row, status)"
              >
                <el-button link type="warning" :loading="switchingCameraId === row.id">状态切换</el-button>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item command="online" :disabled="row.status === 'online'">在线</el-dropdown-item>
                    <el-dropdown-item command="offline" :disabled="row.status === 'offline'">离线</el-dropdown-item>
                    <el-dropdown-item command="disabled" :disabled="row.status === 'disabled'">停用</el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
              <el-button link type="danger" :loading="switchingCameraId === row.id" @click="deleteCamera(row)">删除</el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>
      <div class="record-count">共 {{ cameraTotal }} 个摄像头</div>
    </div>

    <el-dialog v-model="dialogVisible" :title="editingCameraId ? '编辑摄像头' : '新增摄像头'" width="560px">
      <el-form label-position="top" :model="cameraForm">
        <el-form-item label="名称" required><el-input v-model="cameraForm.name" placeholder="摄像头名称" /></el-form-item>
        <el-form-item label="编码"><el-input v-model="cameraForm.code" placeholder="不填则后端自动生成 CAM001" /></el-form-item>
        <el-form-item label="位置"><el-input v-model="cameraForm.location" placeholder="安装位置" /></el-form-item>
        <el-form-item label="原始流地址" required><el-input v-model="cameraForm.streamUrl" placeholder="rtmp://... / rtsp://..." /></el-form-item>
        <el-form-item label="AI处理流地址"><el-input v-model="cameraForm.processedStreamUrl" placeholder="AI 处理后带框流地址，可为空" /></el-form-item>
        <el-form-item label="实时人脸识别">
          <el-radio-group v-model="cameraForm.includeFaces">
            <el-radio-button :value="true">开启</el-radio-button>
            <el-radio-button :value="false">关闭</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item v-if="editingCameraId" label="启用状态">
          <el-radio-group v-model="cameraForm.enabled">
            <el-radio-button :value="true">已启用</el-radio-button>
            <el-radio-button :value="false">未启用</el-radio-button>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitCamera">
          {{ editingCameraId ? '保存修改' : '保存摄像头' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>
