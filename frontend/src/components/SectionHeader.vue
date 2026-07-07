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
    default: 'planned',
  },
})
</script>

<template>
  <div class="section-header">
    <div>
      <p class="section-kicker">{{ badge }}</p>
      <h3>{{ title }}</h3>
      <p v-if="description" class="section-description">{{ description }}</p>
    </div>
    <slot />
  </div>
</template>
