<script setup>
import { ref } from 'vue'
import SectionHeader from '../components/SectionHeader.vue'
import StatusTag from '../components/StatusTag.vue'
import { cameras, realtimeEvents, systemStatus } from '../data/placeholders'

const activeCamera = ref(cameras[0].id)
</script>

<template>
  <div class="page-grid monitor-page">
    <div class="panel">
      <SectionHeader title="实时监控工作台" description="WebSocket 和视频流服务 planned，当前展示监控调度台结构。">
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
        <SectionHeader title="视频画面" description="深色区域为视频播放器、检测框和警戒区域叠加占位。" />
        <div class="monitor-screen">
          <span class="monitor-label">CAM-01 / planned stream / zone overlay</span>
          <div class="detection-box" data-label="PERSON t-1" style="left: 18%; top: 30%; width: 18%; height: 44%" />
          <div class="detection-box" data-label="unknown" style="left: 52%; top: 22%; width: 14%; height: 38%" />
          <div class="zone-shape" />
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
      <div class="metric-card"><p class="metric-label">当前人数</p><p class="metric-value">2</p></div>
      <div class="metric-card"><p class="metric-label">陌生人</p><p class="metric-value">1</p></div>
      <div class="metric-card"><p class="metric-label">区域入侵</p><p class="metric-value">1</p></div>
      <div class="metric-card"><p class="metric-label">异常行为</p><p class="metric-value">0</p></div>
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
