<script setup>
defineProps({
  title: {
    type: String,
    required: true,
  },
  description: {
    type: String,
    default: '',
  },
  badge: {
    type: String,
    default: '',
  },
})
</script>

<template>
  <div class="section-header">
    <div>
      <div class="section-title-row">
        <h3>{{ title }}</h3>
        <el-tag v-if="badge" size="small" type="warning" effect="plain">{{ badge }}</el-tag>
      </div>
      <p v-if="description" class="section-description">{{ description }}</p>
    </div>
    <slot />
  </div>
</template>
