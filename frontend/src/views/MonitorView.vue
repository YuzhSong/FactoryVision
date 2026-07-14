<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import SectionHeader from '../components/SectionHeader.vue'
import StatusTag from '../components/StatusTag.vue'
import mpegts from 'mpegts.js'
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
const playbackMode = ref('idle')
const playbackStats = ref({
  decodedFps: 0,
  droppedFrames: 0,
  packetsLost: 0,
  jitterMs: 0,
  rttMs: 0,
  transport: '-',
  freezes: 0,
})
const playbackMessage = ref('等待播放 AI 处理后视频流')
const streamStatus = ref(null)
const streamAgeSamples = ref([])
const DETECTION_OPTIONS_STORAGE_KEY = 'factoryvision.monitor.detectionOptions.v1'
const DEFAULT_DETECTION_OPTIONS = {
  includeFaces: false,
  includeHelmet: false,
  includeFall: false,
  includeZone: true,
}
const DETECTION_OPTION_KEYS = Object.keys(DEFAULT_DETECTION_OPTIONS)

const detectionOptions = ref(loadDetectionOptions())

let player = null
let realtimeSocket = null
let sdkPromise = null
let streamStatusTimer = null
let playbackLatencyTimer = null
let playbackStatsTimer = null
let playbackWatchdogTimer = null
let lastDecodedFrames = 0
let lastDecodedAt = 0
let lastDecodedProgressAt = 0
let watchdogRestarting = false

const FLV_MAX_LATENCY_SECONDS = 0.9
const FLV_MIN_REMAIN_SECONDS = 0.2
const FLV_CHASE_TRIGGER_SECONDS = 0.9
const FLV_CHASE_TARGET_SECONDS = 0.18
const WEBRTC_JITTER_BUFFER_TARGET_SECONDS = 0.08

function loadDetectionOptions() {
  if (typeof window === 'undefined') return { ...DEFAULT_DETECTION_OPTIONS }
  try {
    const stored = JSON.parse(window.localStorage.getItem(DETECTION_OPTIONS_STORAGE_KEY) || '{}')
    return DETECTION_OPTION_KEYS.reduce((options, key) => {
      options[key] = typeof stored[key] === 'boolean' ? stored[key] : DEFAULT_DETECTION_OPTIONS[key]
      return options
    }, {})
  } catch (error) {
    return { ...DEFAULT_DETECTION_OPTIONS }
  }
}

function persistDetectionOptions() {
  if (typeof window === 'undefined') return
  const options = DETECTION_OPTION_KEYS.reduce((payload, key) => {
    payload[key] = detectionOptions.value[key] === true
    return payload
  }, {})
  window.localStorage.setItem(DETECTION_OPTIONS_STORAGE_KEY, JSON.stringify(options))
}

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
const detectedRtcUrl = computed(() => {
  const camera = currentCamera.value
  return toRtcUrl(camera?.streamConfig?.playUrl)
    || toRtcUrl(camera?.processedStreamUrl)
    || toRtcUrl(camera?.streamConfig?.outputUrl)
    || toRtcUrl(deriveOutputUrl(camera))
})
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
  const url = detectedPlayUrl.value || detectedRtcUrl.value
  if (!url || !url.startsWith('webrtc://')) {
    return url
  }

  return url
    .replace('webrtc://', 'https://')
    .replace(/\/([^/?]+)(\?.*)?$/, '/$1.flv')
})

function toRtcUrl(url) {
  const value = `${url || ''}`.trim()
  if (!value) return ''
  if (value.startsWith('webrtc://')) return value

  const flvMatch = value.match(/^https?:\/\/([^/:]+)(?::\d+)?\/(.+)\.flv(?:[?#].*)?$/)
  if (flvMatch) {
    return `webrtc://${flvMatch[1]}:8443/${flvMatch[2]}`
  }

  const rtmpMatch = value.match(/^rtmps?:\/\/[^/]+\/(.+)$/)
  if (rtmpMatch) {
    return `webrtc://webrtc.rainycode.cn:8443/${rtmpMatch[1]}`
  }

  return ''
}
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

const playbackHudMetrics = computed(() => ({
  mode: playbackMode.value === 'webrtc' ? 'WebRTC' : (playbackMode.value === 'flv' ? 'HTTP-FLV' : '-'),
  fps: playbackStats.value.decodedFps,
  lost: playbackStats.value.packetsLost,
  jitter: playbackStats.value.jitterMs,
  rtt: playbackStats.value.rttMs,
  transport: playbackStats.value.transport || '-',
}))

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
  return Promise.resolve(mpegts)
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
  return {
    ...config,
    ...streamDetectionPayload(),
    zones: Array.isArray(config.zones) ? config.zones : [],
  }
}

function streamDetectionPayload() {
  return {
    includeFaces: detectionOptions.value.includeFaces === true,
    includeHelmet: detectionOptions.value.includeHelmet === true,
    includeFall: detectionOptions.value.includeFall === true,
    includeZone: detectionOptions.value.includeZone === true,
  }
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
    const response = await camerasApi.startStream(activeCamera.value, streamDetectionPayload())
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

function resetPlaybackStats() {
  playbackStats.value = {
    decodedFps: 0,
    droppedFrames: 0,
    packetsLost: 0,
    jitterMs: 0,
    rttMs: 0,
    transport: '-',
    freezes: 0,
  }
  lastDecodedFrames = 0
  lastDecodedAt = 0
  lastDecodedProgressAt = 0
  watchdogRestarting = false
}

function getPeerConnection() {
  return player?.pc || player?.peerConnection || null
}

function applyReceiverLowLatencyHints() {
  const pc = getPeerConnection()
  if (!pc?.getReceivers) return
  pc.getReceivers()
    .filter((receiver) => receiver.track?.kind === 'video')
    .forEach((receiver) => {
      if ('jitterBufferTarget' in receiver) {
        try {
          receiver.jitterBufferTarget = WEBRTC_JITTER_BUFFER_TARGET_SECONDS
        } catch (error) {
          // Browser support is partial; unsupported receivers should not break playback.
        }
      }
    })
}

async function collectWebRtcStats() {
  const pc = getPeerConnection()
  if (!pc?.getStats) return
  const reports = await pc.getStats()
  let inboundVideo = null
  let selectedPair = null
  let localCandidate = null
  let remoteCandidate = null

  reports.forEach((report) => {
    if (report.type === 'inbound-rtp' && (report.kind === 'video' || report.mediaType === 'video')) {
      inboundVideo = report
    }
    if (report.type === 'candidate-pair' && (report.selected || report.nominated)) {
      selectedPair = report
    }
  })

  if (selectedPair) {
    localCandidate = reports.get(selectedPair.localCandidateId)
    remoteCandidate = reports.get(selectedPair.remoteCandidateId)
  }

  const now = performance.now()
  const decoded = Number(inboundVideo?.framesDecoded) || 0
  const elapsedSeconds = lastDecodedAt ? (now - lastDecodedAt) / 1000 : 0
  const decodedFps = elapsedSeconds > 0 ? Math.max(0, Math.round((decoded - lastDecodedFrames) / elapsedSeconds)) : 0
  if (decoded > lastDecodedFrames) {
    lastDecodedProgressAt = now
  }
  lastDecodedFrames = decoded
  lastDecodedAt = now

  const transport = [
    localCandidate?.protocol || '',
    localCandidate?.candidateType || '',
    remoteCandidate?.candidateType ? `to-${remoteCandidate.candidateType}` : '',
  ].filter(Boolean).join('/')

  playbackStats.value = {
    decodedFps,
    droppedFrames: Number(inboundVideo?.framesDropped) || 0,
    packetsLost: Number(inboundVideo?.packetsLost) || 0,
    jitterMs: Math.round((Number(inboundVideo?.jitter) || 0) * 1000),
    rttMs: Math.round((Number(selectedPair?.currentRoundTripTime) || 0) * 1000),
    transport: transport || '-',
    freezes: Number(inboundVideo?.freezeCount) || 0,
  }
}

function startWebRtcStatsPolling() {
  stopWebRtcStatsPolling()
  playbackStatsTimer = window.setInterval(() => {
    collectWebRtcStats().catch(() => null)
  }, 1000)
}

function stopWebRtcStatsPolling() {
  if (playbackStatsTimer) {
    window.clearInterval(playbackStatsTimer)
    playbackStatsTimer = null
  }
}

function startPlaybackWatchdog() {
  stopPlaybackWatchdog()
  playbackWatchdogTimer = window.setInterval(async () => {
    if (playbackMode.value !== 'webrtc' || playbackStatus.value !== 'connected' || watchdogRestarting) return
    const video = videoRef.value
    const pc = getPeerConnection()
    const iceFailed = ['failed', 'disconnected', 'closed'].includes(pc?.iceConnectionState)
    const stalled = video && video.readyState < HTMLMediaElement.HAVE_CURRENT_DATA
    const noDecodedFrames = lastDecodedProgressAt > 0 && performance.now() - lastDecodedProgressAt > 2500
    if (!iceFailed && !stalled && !noDecodedFrames) return

    watchdogRestarting = true
    playbackMessage.value = 'WebRTC stalled, reconnecting...'
    try {
      await startPlayback({ ensureStream: false, allowFlvFallback: false })
    } catch (error) {
      playbackStatus.value = 'error'
      playbackMessage.value = error.message
    } finally {
      watchdogRestarting = false
    }
  }, 2000)
}

function stopPlaybackWatchdog() {
  if (playbackWatchdogTimer) {
    window.clearInterval(playbackWatchdogTimer)
    playbackWatchdogTimer = null
  }
}

async function startPlayback(options = {}) {
  const { ensureStream = false, allowFlvFallback = false } = options
  stopPlayback()
  if (!detectedPlayUrl.value && !detectedRtcUrl.value) {
    playbackStatus.value = 'idle'
    playbackMode.value = 'idle'
    playbackMessage.value = '当前摄像头未配置可播放地址'
    return
  }
  playbackStatus.value = 'connecting'
  playbackMode.value = detectedRtcUrl.value ? 'webrtc' : 'flv'
  playbackMessage.value = ensureStream ? '正在启动并连接 AI 处理后视频流' : '正在连接 AI 处理后视频流'

  try {
    if (ensureStream) {
      await ensureProcessedStream()
      await refreshStreamStatus()
    }
    if (detectedRtcUrl.value) {
      try {
        await startRtcPlayback()
        return
      } catch (rtcError) {
        if (!allowFlvFallback) {
          throw new Error(`WebRTC playback failed: ${rtcError.message}`)
        }
        playbackMessage.value = `WebRTC 连接失败，切换 HTTP-FLV：${rtcError.message}`
      }
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
    const playUrl = normalizeSrsWebRtcUrl(detectedRtcUrl.value)
    await player.play(playUrl)
    applyReceiverLowLatencyHints()
    lastDecodedProgressAt = performance.now()
    playbackStatus.value = 'connected'
    playbackMode.value = 'webrtc'
    startWebRtcStatsPolling()
    startPlaybackWatchdog()
    playbackMessage.value = `WebRTC playing ${playUrl}`
    playbackMessage.value = `正在播放 ${playUrl}`
}

async function startFlvPlayback() {
  await loadMpegtsSdk()
  if (!mpegts.getFeatureList().mseLivePlayback) {
    throw new Error('当前浏览器不支持 HTTP-FLV MSE 直播播放')
  }

  const playUrl = detectedFlvUrl.value
  player = mpegts.createPlayer({
    type: 'flv',
    url: playUrl,
    isLive: true,
    enableStashBuffer: false,
    liveBufferLatencyChasing: true,
    liveBufferLatencyMaxLatency: FLV_MAX_LATENCY_SECONDS,
    liveBufferLatencyMinRemain: FLV_MIN_REMAIN_SECONDS,
  })

  if (videoRef.value) {
    videoRef.value.srcObject = null
    videoRef.value.muted = true
    player.attachMediaElement(videoRef.value)
  }
  player.load()
  await player.play()
  playbackStatus.value = 'connected'
  playbackMode.value = 'flv'
  playbackMessage.value = `正在播放 ${playUrl}`
  startLiveLatencyChasing()
}

async function restartProcessedStream() {
  if (!activeCamera.value) return
  try {
    playbackMessage.value = '正在应用检测开关'
    await aiServiceApi.stopStream().catch(() => null)
    await wait(500)
    await startPlayback({ ensureStream: true })
  } catch (error) {
    ElMessage.error(error?.message || '检测开关应用失败')
  }
}

function stopPlayback() {
  stopLiveLatencyChasing()
  stopWebRtcStatsPolling()
  stopPlaybackWatchdog()
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
  resetPlaybackStats()
}

function startLiveLatencyChasing() {
  stopLiveLatencyChasing()
  playbackLatencyTimer = window.setInterval(() => {
    const video = videoRef.value
    if (!video || !video.buffered || video.buffered.length === 0) return
    const end = video.buffered.end(video.buffered.length - 1)
    const lag = end - video.currentTime
    if (Number.isFinite(lag) && lag > FLV_CHASE_TRIGGER_SECONDS) {
      video.currentTime = Math.max(0, end - FLV_CHASE_TARGET_SECONDS)
    }
  }, 1000)
}

function stopLiveLatencyChasing() {
  if (playbackLatencyTimer) {
    window.clearInterval(playbackLatencyTimer)
    playbackLatencyTimer = null
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

watch(detectionOptions, () => {
  persistDetectionOptions()
}, { deep: true })

watch(systemStatus, () => {
  syncHeaderStatus()
}, { deep: true, immediate: true })

onMounted(async () => {
  startStreamStatusPolling()
  await loadCameras()
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
            <el-button size="small" plain @click="startPlayback({ allowFlvFallback: true })">FLV 兼容</el-button>
            <el-button size="small" type="primary" @click="startPlayback({ ensureStream: true })">重连</el-button>
          </div>
        </SectionHeader>
        <div class="monitor-screen stream-player" :class="playbackStatus">
          <video ref="videoRef" autoplay playsinline controls muted />
          <div class="stream-head">
            <span>{{ playbackHudMetrics.mode }}</span>
            <span>fps {{ playbackHudMetrics.fps }}</span>
            <span>lost {{ playbackHudMetrics.lost }}</span>
            <span>jitter {{ playbackHudMetrics.jitter }}ms</span>
            <span>rtt {{ playbackHudMetrics.rtt }}ms</span>
            <span>{{ playbackHudMetrics.transport }}</span>
            <span>drop {{ streamHudMetrics.dropped }}</span>
            <span>age {{ streamHudMetrics.age }}ms</span>
          </div>
          <div class="stream-foot">
            <span>原始流：{{ currentCamera?.streamUrl || '未配置' }}</span>
            <span>{{ playbackMessage }}</span>
          </div>
        </div>
        <div class="detection-switch-panel">
          <span class="switch-caption">检测开关</span>
          <div class="detection-switch-item">
            <span>人脸</span>
            <el-switch v-model="detectionOptions.includeFaces" @change="restartProcessedStream" />
          </div>
          <div class="detection-switch-item">
            <span>头盔</span>
            <el-switch v-model="detectionOptions.includeHelmet" @change="restartProcessedStream" />
          </div>
          <div class="detection-switch-item">
            <span>摔倒</span>
            <el-switch v-model="detectionOptions.includeFall" @change="restartProcessedStream" />
          </div>
          <div class="detection-switch-item">
            <span>区域</span>
            <el-switch v-model="detectionOptions.includeZone" @change="restartProcessedStream" />
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

.detection-switch-panel {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px 18px;
  padding: 10px 2px 0;
  color: var(--fv-text-muted);
}

.switch-caption {
  font-size: 13px;
  color: var(--fv-text);
}

.detection-switch-item {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: var(--fv-text-muted);
}

@media (max-width: 1180px) {
  .monitor-layout {
    grid-template-columns: 1fr;
  }
}
</style>
