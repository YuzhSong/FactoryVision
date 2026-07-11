<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import SectionHeader from '../components/SectionHeader.vue'
import { camerasApi, zonesApi } from '../api/modules'

const cameraId = ref('')
const cameras = ref([])
const zones = ref([])
const camerasLoading = ref(false)
const zonesLoading = ref(false)

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
      <SectionHeader title="警戒区域配置" description="区域列表已接入后端接口，多边形绘制和保存仍为 planned。" />
      <div class="filter-row">
        <el-select v-model="cameraId" v-loading="camerasLoading" placeholder="选择摄像头">
          <el-option v-for="camera in cameras" :key="camera.id" :label="camera.name" :value="camera.id" />
        </el-select>
        <el-button type="primary" disabled>保存区域 planned</el-button>
      </div>
      <div class="monitor-screen">
        <span class="monitor-label">Zone editor / planned polygon canvas / footPoint rule</span>
        <div class="zone-shape" />
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
