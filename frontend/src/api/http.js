import axios from 'axios'

const http = axios.create({
  // Default to same-origin `/api` so local phone access can reuse the Vite dev server proxy.
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  timeout: 60000,
})

http.interceptors.request.use((config) => {
  const token = localStorage.getItem('factoryVisionToken')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

let redirectingToLogin = false

http.interceptors.response.use(
  (response) => response.data,
  (error) => {
    const isLoginRequest = error.config?.url?.includes('/auth/login/')
    if (error.response?.status === 401 && !isLoginRequest) {
      localStorage.removeItem('factoryVisionToken')
      localStorage.removeItem('factoryVisionUser')
      if (!redirectingToLogin) {
        redirectingToLogin = true
        const redirect = `${window.location.pathname}${window.location.search}`
        window.location.assign(`/login?redirect=${encodeURIComponent(redirect)}`)
      }
    }
    return Promise.reject(error)
  },
)

export default http
