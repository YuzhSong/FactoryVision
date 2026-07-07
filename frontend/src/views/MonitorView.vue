<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import SectionHeader from '../components/SectionHeader.vue'
import StatusTag from '../components/StatusTag.vue'
import { cameras, realtimeEvents, systemStatus } from '../data/placeholders'

const activeCamera = ref(cameras[0].id)
const videoRef = ref(null)
const playbackStatus = ref('idle')
const playbackMessage = ref('等待播放 AI 处理后视频流')

let player = null
let sdkPromise = null

const currentCamera = computed(() => cameras.find((camera) => camera.id === activeCamera.value) || cameras[0])
const detectedPlayUrl = computed(() => currentCamera.value.playUrl)

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

async function startPlayback() {
  stopPlayback()
  playbackStatus.value = 'connecting'
  playbackMessage.value = '正在连接 AI 处理后视频流'

  try {
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
  } catch (error) {
    playbackStatus.value = 'error'
    playbackMessage.value = error.message
    stopPlayback()
  }
}

function stopPlayback() {
  if (player && typeof player.close === 'function') {
    player.close()
  }
  player = null
  if (videoRef.value) {
    videoRef.value.srcObject = null
  }
}

watch(activeCamera, () => {
  startPlayback()
})

onMounted(() => {
  startPlayback()
})

onBeforeUnmount(() => {
  stopPlayback()
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
        <SectionHeader title="摄像头列表" badge="REST planned" />
        <el-radio-group v-model="activeCamera" class="camera-list">
          <el-radio-button v-for="camera in cameras" :key="camera.id" :label="camera.id">
            {{ camera.name }}
          </el-radio-button>
        </el-radio-group>
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
          <el-button size="small" type="primary" @click="startPlayback">重连</el-button>
        </SectionHeader>
        <div class="monitor-screen stream-player" :class="playbackStatus">
          <video ref="videoRef" autoplay playsinline controls muted />
          <div class="stream-head">
            <span>{{ currentCamera.name }}</span>
            <StatusTag :value="playbackStatus" />
          </div>
          <div class="stream-foot">
            <span>原始流：{{ currentCamera.streamUrl }}</span>
            <span>{{ playbackMessage }}</span>
          </div>
        </div>
      </div>

      <div class="panel">
        <SectionHeader title="实时事件流" badge="WebSocket planned" />
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
      </div>
    </div>

    <div class="metric-grid">
      <div class="metric-card"><p class="metric-label">原始流</p><p class="metric-value">RTMP</p></div>
      <div class="metric-card"><p class="metric-label">带框流</p><p class="metric-value">WebRTC</p></div>
      <div class="metric-card"><p class="metric-label">播放状态</p><p class="metric-value">{{ playbackStatus }}</p></div>
      <div class="metric-card"><p class="metric-label">处理模式</p><p class="metric-value">AI</p></div>
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

@media (max-width: 1180px) {
  .monitor-layout {
    grid-template-columns: 1fr;
  }
}
</style>
