<script setup>
import { ref } from 'vue'
import SectionHeader from '../components/SectionHeader.vue'
import StatusTag from '../components/StatusTag.vue'
import { cameras } from '../data/placeholders'

const dialogVisible = ref(false)
</script>

<template>
  <div class="page-grid">
    <div class="panel table-panel">
      <SectionHeader title="摄像头管理" description="摄像头配置接口 planned，流地址仅作为结构展示。">
        <el-button type="primary" @click="dialogVisible = true">新增摄像头</el-button>
      </SectionHeader>
      <div class="filter-row">
        <el-input placeholder="搜索摄像头" clearable />
        <el-select placeholder="状态" clearable>
          <el-option label="在线" value="online" />
          <el-option label="离线" value="offline" />
          <el-option label="停用" value="disabled" />
        </el-select>
        <el-button type="primary">查询</el-button>
      </div>
      <el-table :data="cameras" stripe>
        <el-table-column prop="name" label="摄像头" min-width="150" />
        <el-table-column prop="location" label="位置" width="130" />
        <el-table-column prop="streamUrl" label="原始流地址" min-width="220" show-overflow-tooltip />
        <el-table-column prop="playUrl" label="播放地址" min-width="220" show-overflow-tooltip />
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
        <el-button type="primary">保存占位</el-button>
      </template>
    </el-dialog>
  </div>
</template>
