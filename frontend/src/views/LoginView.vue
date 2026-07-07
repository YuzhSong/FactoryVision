<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Lock, User } from '@element-plus/icons-vue'

const form = ref({
  username: 'admin',
  password: '',
})

function handleLogin() {
  ElMessage.info('登录接口 planned，当前仅展示前端交互占位')
}
</script>

<template>
  <div class="login-view">
    <div class="login-card">
      <h1>工厂监测</h1>
      <p>实时视频分析监测系统</p>
      <el-alert
        class="login-alert"
        title="登录接口 planned，当前用于演示页面骨架。"
        type="info"
        :closable="false"
        show-icon
      />
      <el-form label-position="top" :model="form">
        <el-form-item label="用户名">
          <el-input v-model="form.username" :prefix-icon="User" placeholder="请输入管理员账号" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="form.password" :prefix-icon="Lock" type="password" placeholder="请输入密码" show-password />
        </el-form-item>
        <el-button type="primary" class="full-width" @click="handleLogin">进入系统</el-button>
      </el-form>
    </div>
  </div>
</template>
