<script setup>
defineProps({
  title: {
    type: String,
    required: true,
  },
  description: {
    type: String,
    required: true,
  },
})
</script>

<template>
  <div class="page-card">
    <div class="page-card__header">
      <h3>{{ title }}</h3>
      <el-tag type="info">Placeholder</el-tag>
    </div>
    <p>{{ description }}</p>
    <el-alert
      title="当前阶段仅完成项目骨架，复杂交互和业务逻辑将在后续阶段逐步接入。"
      type="warning"
      :closable="false"
      show-icon
    />
  </div>
</template>
