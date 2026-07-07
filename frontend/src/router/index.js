import { createRouter, createWebHistory } from 'vue-router'

import MainLayout from '../layouts/MainLayout.vue'
import AlertsView from '../views/AlertsView.vue'
import AttendanceView from '../views/AttendanceView.vue'
import CamerasView from '../views/CamerasView.vue'
import DashboardView from '../views/DashboardView.vue'
import EmployeesView from '../views/EmployeesView.vue'
import LoginView from '../views/LoginView.vue'
import MonitorView from '../views/MonitorView.vue'
import ZonesView from '../views/ZonesView.vue'

const routes = [
  {
    path: '/login',
    name: 'login',
    component: LoginView,
    meta: { title: '登录' },
  },
  {
    path: '/',
    component: MainLayout,
    children: [
      { path: '', redirect: '/dashboard' },
      { path: 'dashboard', name: 'dashboard', component: DashboardView, meta: { title: '首页看板' } },
      { path: 'monitor', name: 'monitor', component: MonitorView, meta: { title: '实时监控' } },
      { path: 'alerts', name: 'alerts', component: AlertsView, meta: { title: '告警中心' } },
      { path: 'employees', name: 'employees', component: EmployeesView, meta: { title: '员工管理' } },
      { path: 'cameras', name: 'cameras', component: CamerasView, meta: { title: '摄像头管理' } },
      { path: 'zones', name: 'zones', component: ZonesView, meta: { title: '区域配置' } },
      { path: 'attendance', name: 'attendance', component: AttendanceView, meta: { title: '考勤统计' } },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to) => {
  const token = localStorage.getItem('factoryVisionToken')

  if (to.path !== '/login' && !token) {
    return {
      path: '/login',
      query: { redirect: to.fullPath },
    }
  }

  if (to.path === '/login' && token) {
    return '/dashboard'
  }

  return true
})

export default router
