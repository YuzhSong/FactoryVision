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
  const text = formatEventText(eventType, payload, message)
  return {
    id: payload.eventId || `${Date.now()}-${Math.random()}`,
    type: eventType,
    level: severity,
    text,
    time: formatEventTime(payload.occurredAt || message?.timestamp || message?.occurredAt),
  }
}

export function normalizeStoredEvent(event) {
  const eventType = event.event_type || event.eventType || 'EVENT_CREATED'
  const payload = event.payload || {}
  const text = formatEventText(eventType, { ...payload, ...event })
  return {
    id: event.id,
    type: eventType,
    level: event.severity || 'normal',
    text,
    time: formatEventTime(event.occurred_at || event.occurredAt),
  }
}

export function prependRealtimeEvent(events, message, limit = 30) {
  const incoming = normalizeRealtimeMessage(message)
  return [incoming, ...(events || []).filter((event) => String(event.id) !== String(incoming.id))].slice(0, limit)
}

function formatEventText(eventType, payload = {}, message = {}) {
  const description = payload.description || message.description
  if (description) return description

  if (eventType === 'face_recognized') {
    const name = payload.name || payload.employeeName || message.name || message.employeeName || 'Unknown'
    const confidence = formatConfidence(payload.confidence ?? payload.similarity ?? message.confidence ?? message.similarity)
    return confidence ? `${name} 置信度 ${confidence}` : name
  }

  const trackId = payload.trackId ? ` trackId ${payload.trackId}` : ''
  const confidence = formatConfidence(payload.confidence ?? message.confidence)
  return `${eventType}${trackId}${confidence ? ` / ${confidence}` : ''}`
}

function formatConfidence(value) {
  const numeric = Number(value)
  if (!Number.isFinite(numeric)) return ''
  return `${(numeric <= 1 ? numeric * 100 : numeric).toFixed(1)}%`
}
