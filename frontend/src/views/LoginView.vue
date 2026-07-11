<script setup>
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Lock, User } from '@element-plus/icons-vue'
import { authApi } from '../api/modules'

const route = useRoute()
const router = useRouter()

const form = ref({
  username: 'admin',
  password: '',
})

const loading = ref(false)

async function handleLogin() {
  if (!form.value.username || !form.value.password) {
    ElMessage.warning('请输入用户名和密码')
    return
  }

  loading.value = true
  try {
    const response = await authApi.login(form.value)
    if (response.code !== 200) {
      ElMessage.error(response.message || '登录失败')
      return
    }

    localStorage.setItem('factoryVisionToken', response.data.token)
    localStorage.setItem('factoryVisionUser', JSON.stringify(response.data.user))
    ElMessage.success('登录成功')
    router.push(route.query.redirect || '/dashboard')
  } catch (error) {
    const message = error.response?.data?.message || '登录失败，请检查账号密码或后端服务'
    ElMessage.error(message)
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-view">
    <div class="login-card">
      <h1>工厂监测</h1>
      <p>实时视频分析监测系统</p>
      <el-alert
        class="login-alert"
        title="已接入后端 /api/auth/login/，请使用后端已创建的账号登录。"
        type="success"
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
        <el-button type="primary" class="full-width" :loading="loading" @click="handleLogin">进入系统</el-button>
      </el-form>
    </div>
  </div>
</template>
