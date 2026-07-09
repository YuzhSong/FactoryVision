<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import SectionHeader from '../components/SectionHeader.vue'
import StatusTag from '../components/StatusTag.vue'
import { camerasApi } from '../api/modules'

const dialogVisible = ref(false)
const loading = ref(false)
const cameraRows = ref([])
const filters = reactive({
  status: '',
})

const loadCameras = async () => {
  loading.value = true
  try {
    const response = await camerasApi.list({
      status: filters.status || undefined,
    })
    cameraRows.value = response?.data?.items || []
  } catch (error) {
    cameraRows.value = []
    ElMessage.error(error?.response?.data?.message || '摄像头列表加载失败')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadCameras()
})
</script>

<template>
  <div class="page-grid">
    <div class="panel table-panel">
      <SectionHeader title="摄像头管理" description="摄像头列表已接入后端接口，新增和编辑接口仍为 planned。">
        <el-button type="primary" @click="dialogVisible = true">新增摄像头</el-button>
      </SectionHeader>
      <div class="filter-row">
        <el-input placeholder="搜索摄像头" clearable />
        <el-select v-model="filters.status" placeholder="状态" clearable>
          <el-option label="在线" value="online" />
          <el-option label="离线" value="offline" />
          <el-option label="停用" value="disabled" />
        </el-select>
        <el-button type="primary" @click="loadCameras">查询</el-button>
      </div>
      <el-table v-loading="loading" :data="cameraRows" stripe>
        <el-table-column prop="name" label="摄像头" min-width="150" />
        <el-table-column prop="location" label="位置" width="130" />
        <el-table-column prop="streamUrl" label="原始流地址" min-width="220" show-overflow-tooltip />
        <el-table-column prop="processedStreamUrl" label="AI处理流地址" min-width="220" show-overflow-tooltip />
        <el-table-column label="状态" width="100"><template #default="{ row }"><StatusTag :value="row.status" /></template></el-table-column>
        <el-table-column label="操作" width="160">
          <template #default>
            <el-button link type="primary">编辑</el-button>
            <el-button link type="warning">停用</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <el-dialog v-model="dialogVisible" title="新增摄像头" width="560px">
      <el-form label-position="top">
        <el-form-item label="名称"><el-input placeholder="摄像头名称" /></el-form-item>
        <el-form-item label="位置"><el-input placeholder="安装位置" /></el-form-item>
        <el-form-item label="原始流地址"><el-input placeholder="rtsp://..." /></el-form-item>
        <el-form-item label="前端播放地址"><el-input placeholder="HLS / WebRTC / FLV 地址，planned" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" disabled>保存 planned</el-button>
      </template>
    </el-dialog>
  </div>
</template>
