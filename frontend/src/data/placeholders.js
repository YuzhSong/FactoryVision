export const systemStatus = [
  { label: 'Backend', value: 'healthy', type: 'success' },
  { label: 'AI Service', value: 'processed stream', type: 'success' },
  { label: 'Video Stream', value: 'SRS online', type: 'success' },
]

export const cameras = [
  {
    id: 1,
    name: '一号车间入口',
    location: '一号车间',
    streamUrl: 'rtmp://81.70.90.222:1935/live/1',
    detectedStreamUrl: 'rtmp://81.70.90.222:1935/live/1_detected',
    playUrl: 'webrtc://webrtc.rainycode.cn:8443/live/1_detected',
    status: 'online',
  },
  {
    id: 2,
    name: '装配线东侧',
    location: '装配线',
    streamUrl: 'rtsp://example/camera-02',
    playUrl: 'planned',
    status: 'offline',
  },
  {
    id: 3,
    name: '危化品通道',
    location: '仓储区',
    streamUrl: 'rtsp://example/camera-03',
    playUrl: 'planned',
    status: 'disabled',
  },
]

export const alerts = [
  {
    id: 101,
    title: '危险区域入侵',
    camera: '一号车间入口',
    type: 'ZONE_WARNING',
    level: 'high',
    status: 'pending',
    time: '2026-07-07 10:18:42',
  },
  {
    id: 102,
    title: '未佩戴安全头盔',
    camera: '装配线东侧',
    type: 'HELMET_WARNING',
    level: 'medium',
    status: 'processing',
    time: '2026-07-07 10:05:31',
  },
  {
    id: 103,
    title: '陌生人进入画面',
    camera: '危化品通道',
    type: 'FACE_RESULT',
    level: 'medium',
    status: 'closed',
    time: '2026-07-07 09:42:16',
  },
]

export const employees = [
  { id: 1, employeeNo: 'E001', name: '张三', department: '生产部', position: '班组长', status: 'active' },
  { id: 2, employeeNo: 'E002', name: '李四', department: '设备部', position: '巡检员', status: 'active' },
  { id: 3, employeeNo: 'E003', name: '王五', department: '仓储部', position: '操作员', status: 'inactive' },
]

export const zones = [
  { id: 1, name: '危险设备区', camera: '一号车间入口', level: 'high', safeDistance: 20, enabled: true },
  { id: 2, name: '叉车通道', camera: '装配线东侧', level: 'medium', safeDistance: 30, enabled: true },
  { id: 3, name: '危化品缓冲区', camera: '危化品通道', level: 'high', safeDistance: 40, enabled: false },
]

export const attendanceRecords = [
  {
    employeeNo: 'E001',
    name: '张三',
    department: '生产部',
    firstSeenAt: '08:10',
    lastSeenAt: '17:58',
    leaveCount: 1,
    status: 'normal',
  },
  {
    employeeNo: 'E002',
    name: '李四',
    department: '设备部',
    firstSeenAt: '08:32',
    lastSeenAt: '17:40',
    leaveCount: 2,
    status: 'abnormal',
  },
]

export const realtimeEvents = [
  { id: 1, type: 'PERSON_DETECTION', level: 'normal', text: '检测到人员 trackId t-1', time: '10:18:42' },
  { id: 2, type: 'ZONE_WARNING', level: 'high', text: '人员进入危险设备区', time: '10:18:45' },
  { id: 3, type: 'FACE_RESULT', level: 'medium', text: '陌生人匹配失败', time: '10:19:03' },
]
