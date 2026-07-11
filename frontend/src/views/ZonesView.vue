<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import SectionHeader from '../components/SectionHeader.vue'
import { camerasApi, zonesApi } from '../api/modules'

const cameraId = ref('')
const cameras = ref([])
const zones = ref([])
const camerasLoading = ref(false)
const zonesLoading = ref(false)
const savingZone = ref(false)
const editorRef = ref(null)
const draftPoints = ref([])
const draggingPointIndex = ref(null)

const zoneForm = reactive({
  name: '',
  type: 'danger',
  enabled: true,
  description: '',
})

const cameraNameById = computed(() => {
  const mapping = {}
  cameras.value.forEach((camera) => {
    mapping[camera.id] = camera.name
  })
  return mapping
})

const zoneRows = computed(() => zones.value.map((zone) => ({
  ...zone,
  cameraName: cameraNameById.value[zone.cameraId] || zone.cameraId,
  pointCount: Array.isArray(zone.points) ? zone.points.length : 0,
})))

const selectedCamera = computed(() => cameras.value.find((camera) => camera.id === cameraId.value) || null)

const polygonPoints = computed(() => draftPoints.value
  .map((point) => `${point.x * 100},${point.y * 100}`)
  .join(' '))

const canPreviewPolygon = computed(() => draftPoints.value.length >= 3)

const clamp = (value) => Math.min(Math.max(value, 0), 1)

const pointFromEvent = (event) => {
  const rect = editorRef.value?.getBoundingClientRect()
  if (!rect) return null

  return {
    x: clamp((event.clientX - rect.left) / rect.width),
    y: clamp((event.clientY - rect.top) / rect.height),
  }
}

const addDraftPoint = (event) => {
  if (!cameraId.value) {
    ElMessage.warning('请先选择摄像头')
    return
  }

  const point = pointFromEvent(event)
  if (!point) return
  draftPoints.value.push(point)
}

const startDragPoint = (index, event) => {
  draggingPointIndex.value = index
  event.currentTarget.setPointerCapture?.(event.pointerId)
}

const dragPoint = (event) => {
  if (draggingPointIndex.value === null) return

  const point = pointFromEvent(event)
  if (!point) return
  draftPoints.value.splice(draggingPointIndex.value, 1, point)
}

const stopDragPoint = () => {
  draggingPointIndex.value = null
}

const removeDraftPoint = (index) => {
  draftPoints.value.splice(index, 1)
}

const undoDraftPoint = () => {
  draftPoints.value.pop()
}

const clearDraftPoints = () => {
  draftPoints.value = []
}

const resetZoneForm = () => {
  Object.assign(zoneForm, {
    name: '',
    type: 'danger',
    enabled: true,
    description: '',
  })
}

const useExamplePolygon = () => {
  draftPoints.value = [
    { x: 0.56, y: 0.45 },
    { x: 0.82, y: 0.43 },
    { x: 0.87, y: 0.72 },
    { x: 0.62, y: 0.78 },
  ]
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

const saveZone = async () => {
  if (!cameraId.value) {
    ElMessage.warning('请先选择摄像头')
    return
  }
  if (!zoneForm.name) {
    ElMessage.warning('请填写区域名称')
    return
  }
  if (!canPreviewPolygon.value) {
    ElMessage.warning('请至少绘制 3 个点位')
    return
  }

  savingZone.value = true
  try {
    await zonesApi.save({
      cameraId: cameraId.value,
      name: zoneForm.name,
      type: zoneForm.type,
      points: draftPoints.value.map((point) => ({
        x: Number(point.x.toFixed(4)),
        y: Number(point.y.toFixed(4)),
      })),
      enabled: zoneForm.enabled,
      description: zoneForm.description,
    })
    ElMessage.success('警戒区域已创建')
    clearDraftPoints()
    resetZoneForm()
    await loadZones()
  } catch (error) {
    ElMessage.error(getApiErrorMessage(error, '区域创建失败'))
  } finally {
    savingZone.value = false
  }
}

const loadCameras = async () => {
  camerasLoading.value = true
  try {
    const response = await camerasApi.list()
    cameras.value = response?.data?.items || []
    if (!cameraId.value && cameras.value.length > 0) {
      cameraId.value = cameras.value[0].id
    }
  } catch (error) {
    cameras.value = []
    ElMessage.error(error?.response?.data?.message || '摄像头列表加载失败')
  } finally {
    camerasLoading.value = false
  }
}

const loadZones = async () => {
  zonesLoading.value = true
  try {
    const response = await zonesApi.list({
      cameraId: cameraId.value || undefined,
    })
    zones.value = response?.data?.items || []
  } catch (error) {
    zones.value = []
    ElMessage.error(error?.response?.data?.message || '区域列表加载失败')
  } finally {
    zonesLoading.value = false
  }
}

watch(cameraId, () => {
  clearDraftPoints()
  resetZoneForm()
  loadZones()
})

onMounted(async () => {
  await loadCameras()
  await loadZones()
})
</script>

<template>
  <div class="page-grid">
    <div class="panel">
      <SectionHeader title="警戒区域配置" description="区域查询和创建已接入后端接口，点位使用 0-1 归一化坐标保存。" />
      <div class="filter-row zone-toolbar">
        <el-select v-model="cameraId" v-loading="camerasLoading" placeholder="选择摄像头">
          <el-option v-for="camera in cameras" :key="camera.id" :label="camera.name" :value="camera.id" />
        </el-select>
        <el-button @click="useExamplePolygon">示例区域</el-button>
        <el-button :disabled="draftPoints.length === 0" @click="undoDraftPoint">撤销点位</el-button>
        <el-button :disabled="draftPoints.length === 0" @click="clearDraftPoints">清空</el-button>
        <el-button type="primary" :loading="savingZone" :disabled="!canPreviewPolygon" @click="saveZone">保存区域</el-button>
      </div>

      <el-form class="zone-form" label-position="top" :model="zoneForm">
        <el-form-item label="区域名称" required>
          <el-input v-model="zoneForm.name" placeholder="例如：危险设备区" />
        </el-form-item>
        <el-form-item label="区域类型">
          <el-select v-model="zoneForm.type">
            <el-option label="危险区域" value="danger" />
            <el-option label="限制区域" value="restricted" />
            <el-option label="工位区域" value="workstation" />
            <el-option label="普通区域" value="general" />
          </el-select>
        </el-form-item>
        <el-form-item label="启用">
          <el-switch v-model="zoneForm.enabled" />
        </el-form-item>
        <el-form-item label="说明">
          <el-input v-model="zoneForm.description" placeholder="区域用途或风险说明" />
        </el-form-item>
      </el-form>

      <div
        ref="editorRef"
        class="monitor-screen zone-editor"
        @pointerdown="addDraftPoint"
        @pointermove="dragPoint"
        @pointerup="stopDragPoint"
        @pointerleave="stopDragPoint"
      >
        <span class="monitor-label">
          {{ selectedCamera?.name || '请选择摄像头' }} / 点击画面添加点位 / 拖动蓝色点调整
        </span>
        <div class="zone-video-meta">
          <strong>{{ selectedCamera?.location || '摄像头位置待接入' }}</strong>
          <span>{{ selectedCamera?.processedStreamUrl || selectedCamera?.streamUrl || '视频流待配置' }}</span>
        </div>
        <svg class="zone-editor-layer" viewBox="0 0 100 100" preserveAspectRatio="none">
          <polygon v-if="canPreviewPolygon" class="zone-draft-fill" :points="polygonPoints" />
          <polyline v-if="draftPoints.length > 1" class="zone-draft-line" :points="polygonPoints" />
          <g
            v-for="(point, index) in draftPoints"
            :key="`${index}-${point.x}-${point.y}`"
            class="zone-point"
            :transform="`translate(${point.x * 100} ${point.y * 100})`"
            @pointerdown.stop="startDragPoint(index, $event)"
            @dblclick.stop="removeDraftPoint(index)"
          >
            <circle r="1.6" />
            <text x="2.4" y="-2">{{ index + 1 }}</text>
          </g>
        </svg>
        <div v-if="draftPoints.length === 0" class="zone-editor-empty">
          <strong>在视频区域中点击开始框选危险区域</strong>
          <span>至少 3 个点形成多边形，双击点位可删除</span>
        </div>
      </div>

      <div class="zone-draft-grid">
        <div class="zone-draft-card">
          <span>当前摄像头</span>
          <strong>{{ selectedCamera?.name || '未选择' }}</strong>
        </div>
        <div class="zone-draft-card">
          <span>点位数量</span>
          <strong>{{ draftPoints.length }}</strong>
        </div>
        <div class="zone-draft-card">
          <span>保存状态</span>
          <strong>{{ canPreviewPolygon ? '可保存' : '待绘制' }}</strong>
        </div>
      </div>
    </div>

    <div class="panel table-panel">
      <SectionHeader title="区域列表" />
      <el-table v-loading="zonesLoading" :data="zoneRows" stripe>
        <el-table-column prop="name" label="区域名称" min-width="160" />
        <el-table-column prop="cameraName" label="摄像头" min-width="150" />
        <el-table-column prop="type" label="类型" width="120" />
        <el-table-column prop="pointCount" label="点位数" width="100" />
        <el-table-column prop="description" label="说明" min-width="180" show-overflow-tooltip />
        <el-table-column label="启用" width="100">
          <template #default="{ row }"><el-switch :model-value="row.enabled" disabled /></template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>
