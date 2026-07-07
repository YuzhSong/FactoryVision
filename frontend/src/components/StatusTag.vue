<script setup>
const props = defineProps({
  value: {
    type: String,
    required: true,
  },
})

const map = {
  online: { label: '在线', type: 'success' },
  offline: { label: '离线', type: 'danger' },
  disabled: { label: '停用', type: 'info' },
  active: { label: '在职', type: 'success' },
  inactive: { label: '停用', type: 'info' },
  pending: { label: '待处理', type: 'warning' },
  processing: { label: '处理中', type: 'primary' },
  closed: { label: '已关闭', type: 'info' },
  high: { label: '高危', type: 'danger' },
  medium: { label: '中危', type: 'warning' },
  low: { label: '低危', type: 'info' },
  normal: { label: '正常', type: 'success' },
  abnormal: { label: '异常', type: 'warning' },
}

const tag = map[props.value] || { label: props.value, type: 'info' }
</script>

<template>
  <el-tag :type="tag.type" effect="light" round>{{ tag.label }}</el-tag>
</template>
