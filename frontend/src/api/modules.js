import http from './http'
import axios from 'axios'

function resolveAiServiceBaseUrl() {
  const configuredUrl = import.meta.env.VITE_AI_SERVICE_BASE_URL
  if (configuredUrl) {
    return configuredUrl
  }
  if (typeof window === 'undefined') {
    return '/ai-service'
  }
  const localHosts = new Set(['127.0.0.1', 'localhost'])
  if (localHosts.has(window.location.hostname)) {
    return '/ai-service'
  }
  return 'http://127.0.0.1:9000'
}

const aiServiceHttp = axios.create({
  baseURL: resolveAiServiceBaseUrl(),
  timeout: 60000,
})

export const authApi = {
  login(data) {
    return http.post('/auth/login/', data)
  },
  logout() {
    return http.post('/auth/logout/')
  },
  me() {
    return http.get('/auth/me/')
  },
}

export const healthApi = {
  getHealth() {
    return http.get('/health/')
  },
}

export const dashboardApi = {
  summary() {
    return http.get('/dashboard/summary/')
  },
}

export const usersApi = {
  getPlaceholder() {
    return http.get('/users/')
  },
  list(params = {}) {
    return http.get('/users/list/', { params })
  },
}

export const employeesApi = {
  getPlaceholder() {
    return http.get('/employees/')
  },
  list(params = {}) {
    return http.get('/employees/list/', { params })
  },
  create(data) {
    return http.post('/employees/', data)
  },
  update(employeeId, data) {
    return http.put(`/employees/${employeeId}/`, data)
  },
  remove(employeeId) {
    return http.delete(`/employees/${employeeId}/delete/`)
  },
}

export const faceApi = {
  enroll(data) {
    return http.post('/face/enroll/', data)
  },
}

export const camerasApi = {
  getPlaceholder() {
    return http.get('/cameras/')
  },
  list(params = {}) {
    return http.get('/cameras/list/', { params })
  },
  create(data) {
    return http.post('/cameras/', data)
  },
  update(cameraId, data) {
    return http.put(`/cameras/${cameraId}/`, data)
  },
  remove(cameraId) {
    return http.delete(`/cameras/${cameraId}/delete/`)
  },
  toggle(cameraId, data) {
    return http.post(`/cameras/${cameraId}/toggle/`, data)
  },
  streamStatus(cameraId) {
    return http.get(`/cameras/${cameraId}/stream/status/`)
  },
  startStream(cameraId) {
    return http.post(`/cameras/${cameraId}/stream/start/`)
  },
  stopStream(cameraId) {
    return http.post(`/cameras/${cameraId}/stream/stop/`)
  },
}

export const zonesApi = {
  getPlaceholder() {
    return http.get('/zones/')
  },
  list(params = {}) {
    return http.get('/zones/list/', { params })
  },
  save(data) {
    return http.post('/zones/', data)
  },
  update(zoneId, data) {
    return http.put(`/zones/${zoneId}/`, data)
  },
  remove(zoneId) {
    return http.delete(`/zones/${zoneId}/`)
  },
}

export const eventsApi = {
  getPlaceholder() {
    return http.get('/events/')
  },
  list(params = {}) {
    return http.get('/events/list/', { params })
  },
}

export const alertsApi = {
  list(params = {}) {
    return http.get('/alerts/list/', { params })
  },
  handle(alertId, data) {
    return http.post(`/alerts/${alertId}/handle/`, data)
  },
}

export const attendanceApi = {
  getPlaceholder() {
    return http.get('/attendance/')
  },
  records(params = {}) {
    return http.get('/attendance/records/', { params })
  },
}

export const aiResultsApi = {
  getPlaceholder() {
    return http.get('/ai-results/')
  },
  report(data) {
    return http.post('/ai-results/report/', data)
  },
}

export const aiServiceApi = {
  startStream(data) {
    return aiServiceHttp.post('/streams/start', data)
  },
  stopStream() {
    return aiServiceHttp.post('/streams/stop')
  },
  streamStatus() {
    return aiServiceHttp.get('/streams/status')
  },
}
