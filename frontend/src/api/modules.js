import http from './http'

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
