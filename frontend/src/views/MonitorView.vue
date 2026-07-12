<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import SectionHeader from '../components/SectionHeader.vue'
import StatusTag from '../components/StatusTag.vue'
import { aiServiceApi, camerasApi, eventsApi } from '../api/modules'
import { createRealtimeConnection } from '../api/realtime'
import { normalizeStoredEvent, prependRealtimeEvent } from '../utils/realtimeEvents'

const activeCamera = ref('')
const cameras = ref([])
const camerasLoading = ref(false)
const realtimeEvents = ref([])
const realtimeStatus = ref('idle')
const videoRef = ref(null)
const playbackStatus = ref('idle')
const playbackMessage = ref('等待播放 AI 处理后视频流')
const streamStatus = ref(null)
const streamAgeSamples = ref([])

let player = null
let realtimeSocket = null
let sdkPromise = null
let flvPromise = null
let streamStatusTimer = null

function syncHeaderStatus() {
  if (typeof window === 'undefined') return
  window.dispatchEvent(new CustomEvent('factory-vision-monitor-status', {
    detail: systemStatus.value,
  }))
}

const systemStatus = computed(() => [
  { label: 'WebSocket', value: realtimeStatus.value, type: realtimeStatus.value === 'connected' ? 'success' : 'warning' },
  { label: 'Video Stream', value: playbackStatus.value, type: playbackStatus.value === 'connected' ? 'success' : 'warning' },
])

const currentCamera = computed(() => cameras.value.find((camera) => String(camera.id) === String(activeCamera.value)) || cameras.value[0] || null)
const detectedPlayUrl = computed(() => currentCamera.value?.processedStreamUrl || currentCamera.value?.playUrl || '')
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
const streamHudMetrics = computed(() => {
  const status = streamStatus.value || {}
  const dropped = Number.isFinite(Number(status.dropped_frames)) ? Number(status.dropped_frames) : 0
  const serviceAverage = Number(status.latest_frame_age_avg_2s_ms)
  const localSamples = streamAgeSamples.value.map((sample) => sample.value)
  const localAverage = localSamples.length
    ? localSamples.reduce((total, value) => total + value, 0) / localSamples.length
    : Number(status.latest_frame_age_ms)
  const age = Number.isFinite(serviceAverage)
    ? Math.round(serviceAverage)
    : (Number.isFinite(localAverage) ? Math.round(localAverage) : 0)
  return { dropped, age }
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

function wait(milliseconds) {
  return new Promise((resolve) => window.setTimeout(resolve, milliseconds))
}

function deriveOutputUrl(camera) {
  const processedUrl = `${camera?.processedStreamUrl || ''}`.trim()
  if (processedUrl.startsWith('rtmp://') || processedUrl.startsWith('rtmps://')) {
    return processedUrl
  }
  const sourceUrl = `${camera?.streamUrl || ''}`.trim()
  const match = sourceUrl.match(/^(rtmps?:\/\/[^/]+\/[^/]+\/)([^/?#]+)$/)
  if (!match) return ''
  return `${match[1]}${match[2]}_detected`
}

function buildAiStreamPayload(camera, failedStartResponse = null) {
  const config = failedStartResponse?.cameraConfig
    || (failedStartResponse?.inputUrl ? failedStartResponse : null)
    || camera?.streamConfig
  if (!config) return null
  return { ...config, zones: Array.isArray(config.zones) ? config.zones : [] }
}

async function ensureProcessedStream() {
  if (!activeCamera.value) return null
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
    const response = await camerasApi.startStream(activeCamera.value)
    const runningStatus = await waitForRunning()
    if (runningStatus?.running) return runningStatus
    return response?.data || null
  } catch (error) {
    const payload = buildAiStreamPayload(currentCamera.value, error?.response?.data?.data)
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

async function refreshStreamStatus() {
  try {
    const response = await aiServiceApi.streamStatus()
    const status = response?.data?.data || response?.data || null
    streamStatus.value = status
    const age = Number(status?.latest_frame_age_ms)
    if (Number.isFinite(age)) {
      const now = Date.now()
      streamAgeSamples.value = [
        ...streamAgeSamples.value.filter((sample) => now - sample.time <= 2000),
        { time: now, value: age },
      ]
    }
  } catch (error) {
    streamStatus.value = null
    streamAgeSamples.value = []
  }
}

function startStreamStatusPolling() {
  stopStreamStatusPolling()
  refreshStreamStatus()
  streamStatusTimer = window.setInterval(refreshStreamStatus, 500)
}

function stopStreamStatusPolling() {
  if (streamStatusTimer) {
    window.clearInterval(streamStatusTimer)
    streamStatusTimer = null
  }
}

async function startPlayback(options = {}) {
  const { ensureStream = false } = options
  stopPlayback()
  if (!detectedPlayUrl.value) {
    playbackStatus.value = 'idle'
    playbackMessage.value = '当前摄像头未配置可播放地址'
    return
  }
  playbackStatus.value = 'connecting'
  playbackMessage.value = ensureStream ? '正在启动并连接 AI 处理后视频流' : '正在连接 AI 处理后视频流'

  try {
    if (ensureStream) {
      await ensureProcessedStream()
      await refreshStreamStatus()
    }
    await startFlvPlayback()
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
      realtimeEvents.value = prependRealtimeEvent(realtimeEvents.value, message)
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
    const activeExists = cameras.value.some((camera) => String(camera.id) === String(activeCamera.value))
    if (!activeCamera.value || !activeExists) {
      activeCamera.value = (cameras.value.find((camera) => camera.status === 'online') || cameras.value[0] || {}).id || ''
    }
  } catch (error) {
    cameras.value = []
    ElMessage.error(error?.response?.data?.message || '摄像头列表加载失败')
  } finally {
    camerasLoading.value = false
  }
}

function selectCamera(camera) {
  if (camera?.status !== 'online') {
    ElMessage.warning('当前摄像头离线，无法启动 AI 处理流')
    return
  }
  activeCamera.value = camera.id
}

watch(activeCamera, () => {
  startPlayback({ ensureStream: true })
  loadEventHistory()
  connectRealtime()
})

watch(systemStatus, () => {
  syncHeaderStatus()
}, { deep: true, immediate: true })

onMounted(async () => {
  startStreamStatusPolling()
  await loadCameras()
  if (activeCamera.value) {
    await loadEventHistory()
    startPlayback({ ensureStream: true })
    connectRealtime()
  }
})

onBeforeUnmount(() => {
  if (typeof window !== 'undefined') {
    window.dispatchEvent(new CustomEvent('factory-vision-monitor-status', { detail: null }))
  }
  stopPlayback()
  stopStreamStatusPolling()
  closeRealtimeConnection()
})
</script>

<template>
  <div class="page-grid monitor-page">
    <div class="monitor-layout">
      <div class="panel">
        <SectionHeader title="摄像头列表" />
        <el-empty v-if="!camerasLoading && cameras.length === 0" description="暂无摄像头数据" />
        <div v-loading="camerasLoading" class="camera-card-list">
          <button
            v-for="camera in cameras"
            :key="camera.id"
            type="button"
            class="camera-select-card"
            :class="{ 'is-active': String(activeCamera) === String(camera.id), 'is-disabled': camera.status !== 'online' }"
            :disabled="camera.status !== 'online'"
            @click="selectCamera(camera)"
          >
            <div class="event-title">
              <strong>{{ camera.name }}</strong>
              <StatusTag :value="camera.status" />
            </div>
            <p class="event-meta">编码：{{ camera.code || '未配置' }}</p>
            <p class="event-meta">位置：{{ camera.location || '未配置位置' }}</p>
          </button>
        </div>
      </div>

      <div class="panel monitor-center">
        <SectionHeader title="AI 处理后视频">
          <div class="stream-actions">
            <el-button size="small" type="primary" @click="startPlayback({ ensureStream: true })">重连</el-button>
          </div>
        </SectionHeader>
        <div class="monitor-screen stream-player" :class="playbackStatus">
          <video ref="videoRef" autoplay playsinline controls muted />
          <div class="stream-head">
            <span>drop {{ streamHudMetrics.dropped }}</span>
            <span>age {{ streamHudMetrics.age }}ms</span>
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
            <p class="event-meta">{{ event.time }}</p>
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
  grid-template-columns: 192px minmax(0, 1fr) 295px;
  gap: 10px;
  align-items: stretch;
  --monitor-list-max-height: min(520px, calc(100vh - 330px));
}

.monitor-layout > .panel {
  height: 100%;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.camera-card-list {
  display: grid;
  gap: 10px;
  max-height: var(--monitor-list-max-height);
  min-height: 0;
  overflow-y: auto;
  padding-right: 4px;
}

.monitor-layout > .panel:not(.monitor-center) .event-list {
  flex: 1;
  max-height: var(--monitor-list-max-height);
  min-height: 0;
  overflow-y: auto;
  padding-right: 4px;
}

.camera-select-card {
  width: 100%;
  padding: 14px;
  border: 1px solid var(--fv-border);
  border-radius: 8px;
  background: var(--fv-panel);
  color: var(--fv-text);
  text-align: left;
  cursor: pointer;
  transition: border-color 180ms ease, box-shadow 180ms ease, background 180ms ease;
}

.camera-select-card .event-title {
  align-items: flex-start;
}

.camera-select-card:hover,
.camera-select-card.is-active {
  border-color: #38bdf8;
  background: rgba(37, 99, 235, 0.12);
  box-shadow: 0 0 0 1px rgba(56, 189, 248, 0.24), 0 10px 24px rgba(15, 23, 42, 0.12);
}

.camera-select-card.is-disabled {
  cursor: not-allowed;
  opacity: 0.68;
}

.camera-select-card.is-disabled:hover {
  border-color: var(--fv-border);
  background: var(--fv-panel);
  box-shadow: none;
}

.camera-select-card:focus-visible {
  outline: 2px solid #38bdf8;
  outline-offset: 2px;
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
