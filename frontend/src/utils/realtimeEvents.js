export function formatEventTime(value) {
  if (!value) return new Date().toLocaleTimeString('zh-CN', { hour12: false })
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleTimeString('zh-CN', { hour12: false })
}

export function normalizeRealtimeMessage(message) {
  const payload = message?.payload || {}
  const eventType = payload.eventType || message?.eventType || message?.type || 'EVENT_CREATED'
  const severity = payload.severity || message?.severity || payload.level || 'normal'
  const trackId = payload.trackId ? ` trackId ${payload.trackId}` : ''
  const confidence = typeof payload.confidence === 'number' ? ` / ${(payload.confidence * 100).toFixed(1)}%` : ''
  return {
    id: payload.eventId || `${Date.now()}-${Math.random()}`,
    type: eventType,
    level: severity,
    text: `${eventType}${trackId}${confidence}`,
    time: formatEventTime(payload.occurredAt || message?.timestamp || message?.occurredAt),
  }
}

export function normalizeStoredEvent(event) {
  const eventType = event.event_type || event.eventType || 'EVENT_CREATED'
  const trackId = event.trackId ? ` trackId ${event.trackId}` : ''
  const confidence = typeof event.confidence === 'number' ? ` / ${(event.confidence * 100).toFixed(1)}%` : ''
  return {
    id: event.id,
    type: eventType,
    level: event.severity || 'normal',
    text: `${eventType}${trackId}${confidence}`,
    time: formatEventTime(event.occurred_at || event.occurredAt),
  }
}

export function prependRealtimeEvent(events, message, limit = 30) {
  const incoming = normalizeRealtimeMessage(message)
  return [incoming, ...(events || []).filter((event) => String(event.id) !== String(incoming.id))].slice(0, limit)
}
