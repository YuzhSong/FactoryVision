import assert from 'node:assert/strict'
import test from 'node:test'

import { normalizeStoredEvent, prependRealtimeEvent } from '../src/utils/realtimeEvents.js'

test('websocket event is prepended immediately using canonical event type', () => {
  const next = prependRealtimeEvent(
    [{ id: 1, type: 'helmet_violation' }],
    {
      type: 'EVENT_CREATED',
      payload: {
        eventId: 2,
        eventType: 'face_recognized',
        severity: 'info',
        trackId: 't-4',
        occurredAt: '2026-07-12T17:00:00+08:00',
      },
    },
  )
  assert.equal(next[0].id, 2)
  assert.equal(next[0].type, 'face_recognized')
  assert.match(next[0].text, /trackId t-4/)
})

test('duplicate websocket delivery replaces the same event id', () => {
  const message = { payload: { eventId: 2, eventType: 'region_dwell' } }
  const next = prependRealtimeEvent([{ id: 2, type: 'region_dwell' }], message)
  assert.equal(next.length, 1)
})

test('stored canonical event survives page refresh normalization', () => {
  const item = normalizeStoredEvent({
    id: 3,
    event_type: 'helmet_violation',
    trackId: 't-3',
    severity: 'high',
    occurred_at: '2026-07-12T17:00:00+08:00',
  })
  assert.equal(item.type, 'helmet_violation')
  assert.equal(item.level, 'high')
})
