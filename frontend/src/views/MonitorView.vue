<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import SectionHeader from '../components/SectionHeader.vue'
import StatusTag from '../components/StatusTag.vue'
import { camerasApi, eventsApi } from '../api/modules'
import { createRealtimeConnection } from '../api/realtime'

const activeCamera = ref('')
const cameras = ref([])
const camerasLoading = ref(false)
const realtimeEvents = ref([])
const realtimeStatus = ref('idle')
const videoRef = ref(null)
const playbackStatus = ref('idle')
const playbackMessage = ref('等待播放 AI 处理后视频流')
const playbackMode = ref('flv')

let player = null
let realtimeSocket = null
let sdkPromise = null
let flvPromise = null

const systemStatus = computed(() => [
  { label: 'Backend', value: cameras.value.length ? 'connected' : 'waiting', type: cameras.value.length ? 'success' : 'warning' },
  { label: 'WebSocket', value: realtimeStatus.value, type: realtimeStatus.value === 'connected' ? 'success' : 'warning' },
  { label: 'Video Stream', value: playbackStatus.value, type: playbackStatus.value === 'connected' ? 'success' : 'warning' },
])

const currentCamera = computed(() => cameras.value.find((camera) => camera.id === activeCamera.value) || cameras.value[0] || null)
const detectedPlayUrl = computed(() => currentCamera.value?.playUrl || currentCamera.value?.processedStreamUrl || currentCamera.value?.streamUrl || '')
const monitorStats = computed(() => {
  const highRiskTypes = new Set(['high', 'medium'])
  const highRiskCount = realtimeEvents.value.filter((event) => highRiskTypes.has(event.level)).length

  return [
    { label: '在线摄像头', value: `${cameras.value.filter((camera) => camera.status === 'online').length}/${cameras.value.length}` },
    { label: '事件缓存', value: realtimeEvents.value.length },
    { label: '中高危事件', value: highRiskCount },
    { label: '当前通道', value: currentCamera.value?.code || currentCamera.value?.name || '未选择' },
  ]
})
const detectedFlvUrl = computed(() => {
  const url = detectedPlayUrl.value
  if (!url || !url.startsWith('webrtc://')) {
    return url
  }

  return url
    .replace('webrtc://', 'https://')
    .replace(/\/([^/?]+)(\?.*)?$/, '/$1.flv')
})

function normalizeSrsWebRtcUrl(url) {
  if (!url || !url.startsWith('webrtc://')) {
    return url
  }

  const [base, queryString = ''] = url.split('?')
  const params = new URLSearchParams(queryString)
  if (!params.has('schema')) {
    params.set('schema', 'https')
  }

  return `${base}?${params.toString()}`
}

function loadScript(src) {
  return new Promise((resolve, reject) => {
    const existing = document.querySelector(`script[src="${src}"]`)
    if (existing) {
      if (existing.dataset.loaded === 'true') {
        resolve()
        return
      }
      existing.addEventListener('load', () => resolve(), { once: true })
      existing.addEventListener('error', () => reject(new Error(`脚本加载失败: ${src}`)), { once: true })
      return
    }

    const script = document.createElement('script')
    script.src = src
    script.async = true
    script.onload = () => {
      script.dataset.loaded = 'true'
      resolve()
    }
    script.onerror = () => reject(new Error(`脚本加载失败: ${src}`))
    document.head.appendChild(script)
  })
}

function loadSrsSdk() {
  if (window.SrsRtcPlayerAsync) {
    return Promise.resolve()
  }

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

function loadMpegtsSdk() {
  if (window.mpegts) {
    return Promise.resolve()
  }

  if (!flvPromise) {
    flvPromise = loadScript('https://webrtc.rainycode.cn:8443/players/js/mpegts-1.7.2.min.js')
      .catch((error) => {
        flvPromise = null
        throw error
      })
  }

  return flvPromise
}

async function startPlayback() {
  stopPlayback()
  if (!detectedPlayUrl.value) {
    playbackStatus.value = 'idle'
    playbackMessage.value = '当前摄像头未配置可播放地址'
    return
  }
  playbackStatus.value = 'connecting'
  playbackMessage.value = '正在连接 AI 处理后视频流'

  try {
    if (playbackMode.value === 'flv') {
      await startFlvPlayback()
      return
    }

    await startRtcPlayback()
  } catch (error) {
    playbackStatus.value = 'error'
    playbackMessage.value = error.message
    stopPlayback()
  }
}

async function startRtcPlayback() {
    await loadSrsSdk()
    player = new window.SrsRtcPlayerAsync()
    if (videoRef.value) {
      videoRef.value.srcObject = player.stream
      videoRef.value.muted = true
    }
    const playUrl = normalizeSrsWebRtcUrl(detectedPlayUrl.value)
    await player.play(playUrl)
    playbackStatus.value = 'connected'
    playbackMessage.value = `正在播放 ${playUrl}`
}

async function startFlvPlayback() {
  await loadMpegtsSdk()
  if (!window.mpegts?.getFeatureList().mseLivePlayback) {
    throw new Error('当前浏览器不支持 HTTP-FLV MSE 直播播放')
  }

  const playUrl = detectedFlvUrl.value
  player = window.mpegts.createPlayer({
    type: 'flv',
    url: playUrl,
    isLive: true,
    enableStashBuffer: false,
  })

  if (videoRef.value) {
    videoRef.value.srcObject = null
    videoRef.value.muted = true
    player.attachMediaElement(videoRef.value)
  }
  player.load()
  await player.play()
  playbackStatus.value = 'connected'
  playbackMessage.value = `正在播放 ${playUrl}`
}

function stopPlayback() {
  if (player && typeof player.close === 'function') {
    player.close()
  }
  if (player && typeof player.destroy === 'function') {
    player.destroy()
  }
  player = null
  if (videoRef.value) {
    videoRef.value.srcObject = null
    videoRef.value.removeAttribute('src')
  }
}

function formatTime(value) {
  if (!value) return new Date().toLocaleTimeString('zh-CN', { hour12: false })
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleTimeString('zh-CN', { hour12: false })
}

function normalizeRealtimeMessage(message) {
  const payload = message?.payload || {}
  const eventType = payload.eventType || message.eventType || message.type || 'EVENT_CREATED'
  const severity = payload.severity || message.severity || payload.level || 'normal'
  const trackId = payload.trackId ? ` trackId ${payload.trackId}` : ''
  const confidence = typeof payload.confidence === 'number' ? ` / ${(payload.confidence * 100).toFixed(1)}%` : ''

  return {
    id: payload.eventId || `${Date.now()}-${Math.random()}`,
    type: eventType,
    level: severity,
    text: `${eventType}${trackId}${confidence}`,
    time: formatTime(payload.occurredAt || message.timestamp || message.occurredAt),
  }
}

function normalizeStoredEvent(event) {
  const eventType = event.event_type || event.eventType || 'EVENT_CREATED'
  const trackId = event.trackId ? ` trackId ${event.trackId}` : ''
  const confidence = typeof event.confidence === 'number' ? ` / ${(event.confidence * 100).toFixed(1)}%` : ''

  return {
    id: event.id,
    type: eventType,
    level: event.severity || 'normal',
    text: `${eventType}${trackId}${confidence}`,
    time: formatTime(event.occurred_at || event.occurredAt),
  }
}

function closeRealtimeConnection() {
  if (realtimeSocket) {
    realtimeSocket.close()
    realtimeSocket = null
  }
}

function connectRealtime() {
  closeRealtimeConnection()
  if (!activeCamera.value) {
    realtimeStatus.value = 'idle'
    return
  }

  realtimeStatus.value = 'connecting'
  const token = localStorage.getItem('factoryVisionToken')
  realtimeSocket = createRealtimeConnection(activeCamera.value, token, {
    onOpen: () => {
      realtimeStatus.value = 'connected'
    },
    onClose: () => {
      realtimeStatus.value = 'closed'
    },
    onError: () => {
      realtimeStatus.value = 'error'
    },
    onMessage: (message) => {
      realtimeEvents.value = [normalizeRealtimeMessage(message), ...realtimeEvents.value].slice(0, 30)
    },
  })
}

async function loadEventHistory() {
  if (!activeCamera.value) return
  try {
    const response = await eventsApi.list({ cameraId: activeCamera.value })
    realtimeEvents.value = (response?.data?.items || [])
      .filter((event) => !event.cameraId || String(event.cameraId) === String(activeCamera.value))
      .slice(0, 30)
      .map(normalizeStoredEvent)
  } catch (error) {
    realtimeEvents.value = []
  }
}

async function loadCameras() {
  camerasLoading.value = true
  try {
    const response = await camerasApi.list()
    cameras.value = response?.data?.items || []
    if (!activeCamera.value && cameras.value.length > 0) {
      activeCamera.value = cameras.value[0].id
    }
  } catch (error) {
    cameras.value = []
    ElMessage.error(error?.response?.data?.message || '摄像头列表加载失败')
  } finally {
    camerasLoading.value = false
  }
}

watch(activeCamera, () => {
  startPlayback()
  loadEventHistory()
  connectRealtime()
})

watch(playbackMode, () => {
  startPlayback()
})

onMounted(async () => {
  await loadCameras()
  if (activeCamera.value) {
    await loadEventHistory()
    startPlayback()
    connectRealtime()
  }
})

onBeforeUnmount(() => {
  stopPlayback()
  closeRealtimeConnection()
})
</script>

<template>
  <div class="page-grid monitor-page">
    <div class="panel">
      <SectionHeader title="实时监控工作台" description="当前播放 AI Service 回推到 SRS 的带框 WebRTC 视频流。">
        <div class="status-strip">
          <span v-for="item in systemStatus" :key="item.label" class="status-pill">
            <i class="status-dot" :class="item.type" />{{ item.label }}: {{ item.value }}
          </span>
        </div>
      </SectionHeader>
    </div>

    <div class="monitor-layout">
      <div class="panel">
        <SectionHeader title="摄像头列表" badge="REST" />
        <el-radio-group v-model="activeCamera" v-loading="camerasLoading" class="camera-list">
          <el-radio-button v-for="camera in cameras" :key="camera.id" :label="camera.id">
            {{ camera.name }}
          </el-radio-button>
        </el-radio-group>
        <el-empty v-if="!camerasLoading && cameras.length === 0" description="暂无摄像头数据" />
        <div class="event-list">
          <div v-for="camera in cameras" :key="camera.id" class="event-item">
            <div class="event-title">
              <strong>{{ camera.name }}</strong>
              <StatusTag :value="camera.status" />
            </div>
            <p class="placeholder-note">{{ camera.location }}</p>
          </div>
        </div>
      </div>

      <div class="panel monitor-center">
        <SectionHeader title="AI 处理后视频" description="画面由 AI Service 拉流检测后写入检测框，再回推到 SRS 播放。">
          <div class="stream-actions">
            <el-radio-group v-model="playbackMode" size="small">
              <el-radio-button value="flv">HTTP-FLV</el-radio-button>
              <el-radio-button value="rtc">WebRTC</el-radio-button>
            </el-radio-group>
            <el-button size="small" type="primary" @click="startPlayback">重连</el-button>
          </div>
        </SectionHeader>
        <div class="monitor-screen stream-player" :class="playbackStatus">
          <video ref="videoRef" autoplay playsinline controls muted />
          <div class="stream-head">
            <span>{{ currentCamera?.name || '未选择摄像头' }}</span>
            <StatusTag :value="playbackStatus" />
          </div>
          <div class="stream-foot">
            <span>原始流：{{ currentCamera?.streamUrl || '未配置' }}</span>
            <span>{{ playbackMessage }}</span>
          </div>
        </div>
      </div>

      <div class="panel">
        <SectionHeader title="实时事件流" :badge="realtimeStatus" />
        <div class="event-list">
          <div v-for="event in realtimeEvents" :key="event.id" class="event-item">
            <div class="event-title">
              <strong>{{ event.type }}</strong>
              <StatusTag :value="event.level" />
            </div>
            <p>{{ event.text }}</p>
            <p class="placeholder-note">{{ event.time }}</p>
          </div>
        </div>
        <el-empty v-if="realtimeEvents.length === 0" description="等待实时事件推送" />
      </div>
    </div>

    <div class="metric-grid">
      <div v-for="item in monitorStats" :key="item.label" class="metric-card">
        <p class="metric-label">{{ item.label }}</p>
        <p class="metric-value">{{ item.value }}</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.monitor-layout {
  display: grid;
  grid-template-columns: 260px minmax(0, 1fr) 300px;
  gap: 18px;
}

.camera-list {
  display: grid;
  gap: 10px;
  margin-bottom: 16px;
}

.camera-list :deep(.el-radio-button__inner) {
  width: 100%;
  border-left: var(--el-border);
  border-radius: 8px;
  text-align: left;
}

.stream-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

@media (max-width: 1180px) {
  .monitor-layout {
    grid-template-columns: 1fr;
  }
}
</style>
