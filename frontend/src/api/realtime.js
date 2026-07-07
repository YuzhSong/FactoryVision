const defaultWsBaseUrl = () => {
  const apiBase = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api'
  return apiBase.replace(/^http/, 'ws').replace(/\/api\/?$/, '')
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
