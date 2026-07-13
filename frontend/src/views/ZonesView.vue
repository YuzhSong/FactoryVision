<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import SectionHeader from '../components/SectionHeader.vue'
import mpegts from 'mpegts.js'
import { aiServiceApi, camerasApi, zonesApi } from '../api/modules'

const cameraId = ref('')
const cameras = ref([])
const zones = ref([])
const camerasLoading = ref(false)
const zonesLoading = ref(false)
const savingZone = ref(false)
const editorRef = ref(null)
const videoRef = ref(null)
const draftPoints = ref([])
const draggingPointIndex = ref(null)
const editingZoneId = ref(null)
const playbackStatus = ref('idle')
const playbackMessage = ref('等待处理后视频流')
const switchingZoneId = ref(null)
const videoLayout = reactive({ left: 0, top: 0, width: 0, height: 0 })

let player = null
let sdkPromise = null
let resizeObserver = null
let playbackLatencyTimer = null

const zoneForm = reactive({
  name: '',
  type: 'danger',
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
const detectedPlayUrl = computed(() => selectedCamera.value?.processedStreamUrl || selectedCamera.value?.playUrl || '')
const detectedFlvUrl = computed(() => {
  const url = detectedPlayUrl.value
  if (!url || !url.startsWith('webrtc://')) return url
  return url.replace('webrtc://', 'https://').replace(/\/([^/?]+)(\?.*)?$/, '/$1.flv')
})

const polygonPoints = computed(() => draftPoints.value
  .map((point) => `${point.x * 100},${point.y * 100}`)
  .join(' '))

const canPreviewPolygon = computed(() => draftPoints.value.length >= 3)
const savedPolygons = computed(() => zones.value
  .filter((zone) => Array.isArray(zone.points) && zone.points.length >= 3)
  .map((zone) => ({
    ...zone,
    svgPoints: zone.points.map((point) => `${Number(point.x) > 1 ? Number(point.x) : Number(point.x) * 100},${Number(point.y) > 1 ? Number(point.y) : Number(point.y) * 100}`).join(' '),
  })))

const clamp = (value) => Math.min(Math.max(value, 0), 1)
const withTimeout = (promise, milliseconds, message) => new Promise((resolve, reject) => {
  const timeout = window.setTimeout(() => reject(new Error(message)), milliseconds)
  Promise.resolve(promise).then(
    (value) => { window.clearTimeout(timeout); resolve(value) },
    (error) => { window.clearTimeout(timeout); reject(error) },
  )
})
const overlayStyle = computed(() => ({
  left: `${videoLayout.left}px`,
  top: `${videoLayout.top}px`,
  width: `${videoLayout.width}px`,
  height: `${videoLayout.height}px`,
}))

const updateVideoLayout = () => {
  const container = editorRef.value
  const video = videoRef.value
  if (!container || !video) return
  const containerWidth = container.clientWidth
  const containerHeight = container.clientHeight
  const videoWidth = video.videoWidth || 16
  const videoHeight = video.videoHeight || 9
  const scale = Math.min(containerWidth / videoWidth, containerHeight / videoHeight)
  videoLayout.width = videoWidth * scale
  videoLayout.height = videoHeight * scale
  videoLayout.left = (containerWidth - videoLayout.width) / 2
  videoLayout.top = (containerHeight - videoLayout.height) / 2
}

const loadScript = (src) => new Promise((resolve, reject) => {
  const existing = document.querySelector(`script[src="${src}"]`)
  if (existing) {
    if (existing.dataset.loaded === 'true') return resolve()
    existing.addEventListener('load', resolve, { once: true })
    existing.addEventListener('error', () => reject(new Error(`播放器脚本加载失败: ${src}`)), { once: true })
    return
  }
  const script = document.createElement('script')
  script.src = src
  script.async = true
  script.onload = () => {
    script.dataset.loaded = 'true'
    resolve()
  }
  script.onerror = () => reject(new Error(`播放器脚本加载失败: ${src}`))
  document.head.appendChild(script)
})

const loadMpegtsSdk = () => {
  return Promise.resolve(mpegts)
}

const loadSrsSdk = () => {
  if (window.SrsRtcPlayerAsync) return Promise.resolve()
  if (!sdkPromise) {
    sdkPromise = loadScript('https://webrtc.rainycode.cn:8443/players/js/adapter-7.4.0.min.js')
      .then(() => loadScript('https://webrtc.rainycode.cn:8443/players/js/srs.sdk.js'))
      .catch((error) => {
        sdkPromise = null
        throw error
      })
  }
  return sdkPromise
}

const wait = (milliseconds) => new Promise((resolve) => window.setTimeout(resolve, milliseconds))

const deriveOutputUrl = (camera) => {
  const processedUrl = `${camera?.processedStreamUrl || ''}`.trim()
  if (processedUrl.startsWith('rtmp://') || processedUrl.startsWith('rtmps://')) {
    return processedUrl
  }
  const sourceUrl = `${camera?.streamUrl || ''}`.trim()
  const match = sourceUrl.match(/^(rtmps?:\/\/[^/]+\/[^/]+\/)([^/?#]+)$/)
  if (!match) return ''
  return `${match[1]}${match[2]}_detected`
}

const buildAiStreamPayload = (camera, failedStartResponse = null) => {
  const config = failedStartResponse?.cameraConfig
    || (failedStartResponse?.inputUrl ? failedStartResponse : null)
    || camera?.streamConfig
  if (!config) return null
  return { ...config, zones: Array.isArray(config.zones) ? config.zones : [] }
}

const ensureProcessedStream = async () => {
  if (!cameraId.value) return null
  playbackMessage.value = '正在启动 AI 处理流'
  const waitForRunning = async () => {
    let latestStatus = null
    for (let attempt = 0; attempt < 4; attempt += 1) {
      await wait(1500)
      const statusResponse = await aiServiceApi.streamStatus()
      latestStatus = statusResponse?.data?.data || statusResponse?.data || null
      if (latestStatus?.running) return latestStatus
    }
    return latestStatus
  }
  try {
    const response = await camerasApi.startStream(cameraId.value)
    const runningStatus = await waitForRunning()
    if (runningStatus?.running) return runningStatus
    return response?.data || null
  } catch (error) {
    const payload = buildAiStreamPayload(selectedCamera.value, error?.response?.data?.data)
    if (!payload?.cameraId || !payload?.inputUrl || !payload?.outputUrl || !payload?.playUrl) {
      throw error
    }
    let lastStatus = null
    for (let attempt = 0; attempt < 2; attempt += 1) {
      await aiServiceApi.startStream(payload)
      lastStatus = await waitForRunning()
      if (lastStatus?.running) return lastStatus
    }
    if (lastStatus?.last_error) {
      throw new Error(String(lastStatus.last_error).split('\n')[0])
    }
    throw error
  }
}

const stopPlayback = () => {
  stopLiveLatencyChasing()
  player?.close?.()
  player?.destroy?.()
  player = null
  if (videoRef.value) {
    videoRef.value.srcObject = null
    videoRef.value.removeAttribute('src')
  }
}

const startLiveLatencyChasing = () => {
  stopLiveLatencyChasing()
  playbackLatencyTimer = window.setInterval(() => {
    const video = videoRef.value
    if (!video || !video.buffered || video.buffered.length === 0) return
    const end = video.buffered.end(video.buffered.length - 1)
    const lag = end - video.currentTime
    if (Number.isFinite(lag) && lag > 2) {
      video.currentTime = Math.max(0, end - 0.35)
    }
  }, 1000)
}

const stopLiveLatencyChasing = () => {
  if (playbackLatencyTimer) {
    window.clearInterval(playbackLatencyTimer)
    playbackLatencyTimer = null
  }
}

const startPlayback = async (options = {}) => {
  const { ensureStream = false } = options
  stopPlayback()
  const playUrl = detectedFlvUrl.value
  if (!playUrl) {
    playbackStatus.value = 'idle'
    playbackMessage.value = '当前摄像头未配置处理后播放地址'
    return
  }
  playbackStatus.value = 'connecting'
  playbackMessage.value = ensureStream ? '正在启动并连接处理后视频流' : '正在连接处理后视频流'
  try {
    if (ensureStream) {
      await ensureProcessedStream()
    }
    await loadMpegtsSdk()
    if (!mpegts.getFeatureList().mseLivePlayback) throw new Error('当前浏览器不支持 HTTP-FLV 直播播放')
    player = mpegts.createPlayer({
      type: 'flv',
      url: playUrl,
      isLive: true,
      enableStashBuffer: false,
      liveBufferLatencyChasing: true,
      liveBufferLatencyMaxLatency: 2,
      liveBufferLatencyMinRemain: 0.5,
    })
    player.attachMediaElement(videoRef.value)
    player.load()
    await withTimeout(player.play(), 8000, '处理后视频流连接超时，请检查 SRS 或 processedStreamUrl')
    playbackStatus.value = 'connected'
    playbackMessage.value = `正在播放 ${playUrl}`
    startLiveLatencyChasing()
  } catch (error) {
    playbackStatus.value = 'error'
    playbackMessage.value = error.message
    stopPlayback()
  }
}

const pointFromEvent = (event) => {
  const rect = editorRef.value?.getBoundingClientRect()
  if (!rect || !videoLayout.width || !videoLayout.height) return null

  return {
    x: clamp((event.clientX - rect.left - videoLayout.left) / videoLayout.width),
    y: clamp((event.clientY - rect.top - videoLayout.top) / videoLayout.height),
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
    const payload = {
      cameraId: cameraId.value,
      name: zoneForm.name,
      type: zoneForm.type,
      points: draftPoints.value.map((point) => ({
        x: Number(point.x.toFixed(4)),
        y: Number(point.y.toFixed(4)),
      })),
      enabled: editingZoneId.value
        ? zones.value.find((zone) => zone.id === editingZoneId.value)?.enabled !== false
        : true,
      description: zoneForm.description,
    }
    if (editingZoneId.value) await zonesApi.update(editingZoneId.value, payload)
    else await zonesApi.save(payload)
    ElMessage.success('警戒区域已创建')
    clearDraftPoints()
    resetZoneForm()
    editingZoneId.value = null
    await loadZones()
  } catch (error) {
    ElMessage.error(getApiErrorMessage(error, '区域创建失败'))
  } finally {
    savingZone.value = false
  }
}

const editZone = (zone) => {
  editingZoneId.value = zone.id
  Object.assign(zoneForm, {
    name: zone.name,
    type: zone.type,
    description: zone.description || '',
  })
  draftPoints.value = (zone.points || []).map((point) => ({ x: Number(point.x), y: Number(point.y) }))
}

const toggleZoneEnabled = async (zone, enabled) => {
  const previous = zone.enabled !== false
  if (previous === enabled) return
  switchingZoneId.value = zone.id
  zones.value = zones.value.map((item) => (item.id === zone.id ? { ...item, enabled } : item))
  try {
    await zonesApi.update(zone.id, {
      cameraId: zone.cameraId,
      name: zone.name,
      type: zone.type,
      points: zone.points || [],
      enabled,
      description: zone.description || '',
    })
    ElMessage.success(enabled ? '区域已启用' : '区域已停用')
    await loadZones()
  } catch (error) {
    zones.value = zones.value.map((item) => (item.id === zone.id ? { ...item, enabled: previous } : item))
    ElMessage.error(getApiErrorMessage(error, '区域启用状态更新失败'))
  } finally {
    switchingZoneId.value = null
  }
}

const deleteZone = async (zone) => {
  await zonesApi.remove(zone.id)
  if (editingZoneId.value === zone.id) {
    editingZoneId.value = null
    clearDraftPoints()
    resetZoneForm()
  }
  await loadZones()
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
  startPlayback({ ensureStream: true })
})

onMounted(async () => {
  await loadCameras()
  await loadZones()
  resizeObserver = new ResizeObserver(updateVideoLayout)
  if (editorRef.value) resizeObserver.observe(editorRef.value)
})

onBeforeUnmount(() => {
  resizeObserver?.disconnect()
  stopPlayback()
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
        <el-button @click="startPlayback({ ensureStream: true })">重连视频</el-button>
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
        <video ref="videoRef" autoplay playsinline muted @loadedmetadata="updateVideoLayout" />
        <span class="monitor-label">
          {{ selectedCamera?.name || '请选择摄像头' }} / 点击画面添加点位 / 拖动蓝色点调整
        </span>
        <div class="zone-video-meta">
          <strong>{{ selectedCamera?.location || '摄像头位置待接入' }}</strong>
          <span>{{ playbackMessage }}</span>
        </div>
        <svg class="zone-editor-layer" :style="overlayStyle" viewBox="0 0 100 100" preserveAspectRatio="none">
          <g v-for="zone in savedPolygons" :key="`saved-${zone.id}`">
            <polygon class="zone-saved-fill" :points="zone.svgPoints" />
            <text class="zone-saved-label" :x="Number(zone.points[0].x) > 1 ? Number(zone.points[0].x) : Number(zone.points[0].x) * 100" :y="Number(zone.points[0].y) > 1 ? Number(zone.points[0].y) : Number(zone.points[0].y) * 100">{{ zone.name }}</text>
          </g>
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
          <template #default="{ row }">
            <el-switch
              :model-value="row.enabled"
              :loading="switchingZoneId === row.id"
              @change="(value) => toggleZoneEnabled(row, value)"
            />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150">
          <template #default="{ row }">
            <el-button link type="primary" @click="editZone(row)">编辑</el-button>
            <el-button link type="danger" @click="deleteZone(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>
