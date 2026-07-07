<script setup>
import { ref } from 'vue'
import SectionHeader from '../components/SectionHeader.vue'
import StatusTag from '../components/StatusTag.vue'
import { cameras, zones } from '../data/placeholders'

const cameraId = ref(cameras[0].id)
</script>

<template>
  <div class="page-grid">
    <div class="panel">
      <SectionHeader title="警戒区域配置" description="多边形绘制和保存接口 planned，当前展示区域编辑工作区。" />
      <div class="filter-row">
        <el-select v-model="cameraId" placeholder="选择摄像头">
          <el-option v-for="camera in cameras" :key="camera.id" :label="camera.name" :value="camera.id" />
        </el-select>
        <el-button type="primary">保存区域占位</el-button>
      </div>
      <div class="monitor-screen">
        <span class="monitor-label">Zone editor / planned polygon canvas / footPoint rule</span>
        <div class="zone-shape" />
      </div>
    </div>

    <div class="panel table-panel">
      <SectionHeader title="区域列表" />
      <el-table :data="zones" stripe>
        <el-table-column prop="name" label="区域名称" min-width="160" />
        <el-table-column prop="camera" label="摄像头" min-width="150" />
        <el-table-column label="等级" width="100"><template #default="{ row }"><StatusTag :value="row.level" /></template></el-table-column>
        <el-table-column prop="safeDistance" label="安全距离(px)" width="130" />
        <el-table-column label="启用" width="100">
          <template #default="{ row }"><el-switch :model-value="row.enabled" disabled /></template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>
