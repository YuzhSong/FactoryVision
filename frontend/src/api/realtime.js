const defaultWsBaseUrl = () => {
  const apiBase = import.meta.env.VITE_API_BASE_URL || '/api'
  if (/^https?:\/\//i.test(apiBase)) {
    return apiBase.replace(/^http/i, 'ws').replace(/\/api\/?$/, '')
  }
  if (typeof window !== 'undefined') {
    return `${window.location.protocol === 'https:' ? 'wss' : 'ws'}://${window.location.host}`
  }
  return 'ws://127.0.0.1:8000'
}

export function createRealtimeConnection(cameraId, token, handlers = {}) {
  const baseUrl = import.meta.env.VITE_WS_BASE_URL || defaultWsBaseUrl()
  const params = token ? `?token=${encodeURIComponent(token)}` : ''
  const socket = new WebSocket(`${baseUrl}/ws/realtime/${cameraId}/${params}`)

  socket.addEventListener('open', (event) => handlers.onOpen?.(event))
  socket.addEventListener('close', (event) => handlers.onClose?.(event))
  socket.addEventListener('error', (event) => handlers.onError?.(event))
  socket.addEventListener('message', (event) => {
    try {
      handlers.onMessage?.(JSON.parse(event.data), event)
    } catch (error) {
      handlers.onError?.(error)
    }
  })

  return socket
}
