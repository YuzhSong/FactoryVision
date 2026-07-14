<script setup>
import { computed, nextTick, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import SectionHeader from '../components/SectionHeader.vue'
import StatusTag from '../components/StatusTag.vue'
import { aiServiceApi, employeesApi, faceApi } from '../api/modules'

const dialogVisible = ref(false)
const editDialogVisible = ref(false)
const faceDialogVisible = ref(false)
const saving = ref(false)
const enrolling = ref(false)
const faceListLoading = ref(false)
const loading = ref(false)
const switchingEmployeeId = ref(null)
const deletingFaceId = ref(null)
const employeeRows = ref([])
const employeeTotal = ref(0)
const currentEmployee = ref(null)
const employeeFaceRows = ref([])
const employeeFaceStatus = reactive({})
const fileInputRefs = ref({})
const activeCameraKey = ref('')
const activeVideoRef = ref(null)
const canvasRef = ref(null)
let mediaStream = null

const faceShotTypes = [
  { key: 'front', label: '正脸', hint: '请保持正对镜头' },
  { key: 'left', label: '左脸', hint: '请向左侧转头' },
  { key: 'right', label: '右脸', hint: '请向右侧转头' },
]

const faceImages = reactive({
  front: '',
  left: '',
  right: '',
})

const faceDirty = reactive({
  front: false,
  left: false,
  right: false,
})

const faceTypeLabels = {
  front: '正脸',
  left: '左脸',
  right: '右脸',
}

const filters = reactive({
  keyword: '',
  department: '',
  status: '',
  page: 1,
  pageSize: 20,
})

const employeeForm = reactive({
  employeeNo: '',
  name: '',
  department: '',
  position: '',
  phone: '',
})

const editForm = reactive({
  id: null,
  employeeNo: '',
  name: '',
  department: '',
  position: '',
  phone: '',
  status: 'active',
})

const resetEmployeeForm = () => {
  Object.assign(employeeForm, {
    employeeNo: '',
    name: '',
    department: '',
    position: '',
    phone: '',
  })
}

const openCreateDialog = () => {
  resetEmployeeForm()
  dialogVisible.value = true
}

const openEditDialog = (employee) => {
  Object.assign(editForm, {
    id: employee.id,
    employeeNo: employee.employeeNo || '',
    name: employee.name || '',
    department: employee.department || '',
    position: employee.position || '',
    phone: employee.phone || '',
    status: employee.status || 'active',
  })
  editDialogVisible.value = true
}

const departmentOptions = computed(() => {
  const values = employeeRows.value.map((item) => item.department).filter(Boolean)
  return [...new Set(['生产部', '设备部', '仓储部', ...values])]
})

const faceListCards = computed(() => faceShotTypes.map((type) => {
  const faces = employeeFaceRows.value
    .filter((face) => face.faceType === type.key)
    .sort((a, b) => new Date(b.createdAt || 0) - new Date(a.createdAt || 0))

  return {
    ...type,
    face: faces[0] || null,
    count: faces.length,
  }
}))

const hasSavedFaces = computed(() => faceListCards.value.some((item) => item.face))
const hasDirtyFaces = computed(() => faceShotTypes.some((item) => faceDirty[item.key]))
const faceDialogTitle = computed(() => (hasSavedFaces.value ? '已录入人脸' : '人脸录入'))

const loadEmployeeFaceStatuses = async (rows = []) => {
  await Promise.allSettled(rows.map(async (employee) => {
    if (!employee?.id) return
    const response = await employeesApi.faces(employee.id)
    employeeFaceStatus[employee.id] = normalizeFaceRows(response?.data || []).length > 0
  }))
}

const loadEmployees = async () => {
  loading.value = true
  try {
    const response = await employeesApi.list({
      page: filters.page,
      pageSize: filters.pageSize,
      keyword: filters.keyword || undefined,
      department: filters.department || undefined,
      status: filters.status || undefined,
    })
    employeeRows.value = response?.data?.items || []
    employeeTotal.value = response?.data?.total || 0
    await loadEmployeeFaceStatuses(employeeRows.value)
  } catch (error) {
    employeeRows.value = []
    employeeTotal.value = 0
    ElMessage.error(getApiErrorMessage(error, '员工列表加载失败'))
  } finally {
    loading.value = false
  }
}

const queryEmployees = () => {
  filters.page = 1
  loadEmployees()
}

const submitEmployee = async () => {
  if (!employeeForm.employeeNo || !employeeForm.name) {
    ElMessage.warning('请填写工号和姓名')
    return
  }

  saving.value = true
  try {
    const response = await employeesApi.create({ ...employeeForm })
    ElMessage.success('员工档案已提交')
    dialogVisible.value = false
    await loadEmployees()

    if (response?.data?.id) {
      await openFaceDialog({
        id: response.data.id,
        employeeNo: employeeForm.employeeNo,
        name: employeeForm.name,
      })
    }
  } catch (error) {
    ElMessage.error(error?.response?.data?.message || '员工创建接口暂不可用')
  } finally {
    saving.value = false
  }
}

const resetFaceImages = () => {
  faceShotTypes.forEach((item) => {
    faceImages[item.key] = ''
    faceDirty[item.key] = false
  })
}

const syncFaceImagesFromSavedFaces = () => {
  faceShotTypes.forEach((item) => {
    const savedFace = faceListCards.value.find((card) => card.key === item.key)?.face
    faceImages[item.key] = savedFace?.imageUrl || ''
    faceDirty[item.key] = false
  })
}

const openFaceDialog = async (employee) => {
  currentEmployee.value = employee
  stopCamera()
  resetFaceImages()
  employeeFaceRows.value = []
  faceDialogVisible.value = true
  await loadEmployeeFaces()
  syncFaceImagesFromSavedFaces()
}

const normalizeFaceRows = (payload = []) => {
  const rows = Array.isArray(payload)
    ? payload
    : Object.entries(payload || {})
      .filter(([, face]) => Boolean(face))
      .map(([faceType, face]) => ({ ...face, faceType }))

  return rows.map((face) => ({
    id: face.id || face.faceFeatureId,
    faceType: face.faceType,
    label: faceTypeLabels[face.faceType] || face.faceType || '人脸',
    imageUrl: face.imageUrl || face.imagePath || '',
    createdAt: face.createdAt || '',
  }))
}

const getSavedFace = (key) => employeeFaceRows.value.find((face) => face.faceType === key) || null

const getFaceActionLabel = (key) => {
  const savedFace = getSavedFace(key)
  if (savedFace && !faceDirty[key]) return '删除'
  return '清除'
}

const isFaceActionDisabled = (key) => {
  const savedFace = getSavedFace(key)
  return !faceImages[key] && !savedFace
}

const getEmployeeFaceButtonLabel = (employee) => (
  employeeFaceStatus[employee.id] ? '重新录入' : '开始录入'
)

const loadEmployeeFaces = async () => {
  if (!currentEmployee.value?.id) return

  faceListLoading.value = true
  try {
    const response = await employeesApi.faces(currentEmployee.value.id)
    employeeFaceRows.value = normalizeFaceRows(response?.data || [])
    employeeFaceStatus[currentEmployee.value.id] = employeeFaceRows.value.length > 0
  } catch (error) {
    employeeFaceRows.value = []
    if (currentEmployee.value?.id) {
      employeeFaceStatus[currentEmployee.value.id] = false
    }
    ElMessage.error(getApiErrorMessage(error, '人脸列表加载失败'))
  } finally {
    faceListLoading.value = false
  }
}

const refreshEmployeeFaces = async () => {
  await loadEmployeeFaces()
  syncFaceImagesFromSavedFaces()
}

const deleteFace = async (face) => {
  if (!face?.id) return

  try {
    await ElMessageBox.confirm(`确认删除${face.label || '该'}照片？`, '删除人脸照片', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
    })
  } catch (error) {
    return
  }

  deletingFaceId.value = face.id
  try {
    await faceApi.remove(face.id)
    ElMessage.success('人脸照片已删除')
    await refreshEmployeeFaces()
  } catch (error) {
    ElMessage.error(getApiErrorMessage(error, '人脸照片删除失败'))
  } finally {
    deletingFaceId.value = null
  }
}

const closeFaceDialog = () => {
  stopCamera()
  faceDialogVisible.value = false
}

const setFileInputRef = (key, element) => {
  if (element) {
    fileInputRefs.value[key] = element
  }
}

const openFilePicker = (key) => {
  fileInputRefs.value[key]?.click()
}

const stopCamera = () => {
  if (mediaStream) {
    mediaStream.getTracks().forEach((track) => track.stop())
    mediaStream = null
  }
  activeCameraKey.value = ''
  activeVideoRef.value = null
}

const setActiveVideoRef = (element) => {
  if (element) {
    activeVideoRef.value = element
  }
}

const startCameraFor = async (key) => {
  if (!navigator.mediaDevices?.getUserMedia) {
    ElMessage.warning('当前浏览器不支持摄像头拍摄')
    return
  }

  try {
    stopCamera()
    activeCameraKey.value = key
    await nextTick()
    mediaStream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: 'user', width: { ideal: 960 }, height: { ideal: 720 } },
      audio: false,
    })
    if (activeVideoRef.value) {
      activeVideoRef.value.srcObject = mediaStream
      await activeVideoRef.value.play()
    }
  } catch (error) {
    stopCamera()
    ElMessage.error(`无法打开摄像头：${error?.name || '请检查浏览器权限'}`)
  }
}

const fileToDataUrl = (file) => new Promise((resolve, reject) => {
  const reader = new FileReader()
  reader.onload = () => resolve(reader.result)
  reader.onerror = reject
  reader.readAsDataURL(file)
})

const handleFaceFile = async (event, key) => {
  const file = event.target.files?.[0]
  event.target.value = ''

  if (!file) return
  if (!file.type.startsWith('image/')) {
    ElMessage.warning('请选择图片文件')
    return
  }

  faceImages[key] = await fileToDataUrl(file)
  faceDirty[key] = true
}

const clearFaceImage = (key) => {
  faceImages[key] = ''
  faceDirty[key] = false
}

const handleFaceSlotAction = async (key) => {
  const savedFace = getSavedFace(key)
  if (savedFace && !faceDirty[key]) {
    await deleteFace(savedFace)
    return
  }
  clearFaceImage(key)
}

const submitEmployeeEdit = async () => {
  if (!editForm.id) {
    ElMessage.warning('请先选择员工')
    return
  }
  if (!editForm.name) {
    ElMessage.warning('请填写姓名')
    return
  }

  saving.value = true
  try {
    await employeesApi.update(editForm.id, {
      employeeNo: editForm.employeeNo,
      name: editForm.name,
      department: editForm.department,
      position: editForm.position,
      phone: editForm.phone,
      status: editForm.status,
    })
    ElMessage.success('员工信息已保存')
    editDialogVisible.value = false
    await loadEmployees()
  } catch (error) {
    ElMessage.error(getApiErrorMessage(error, '员工信息保存失败'))
  } finally {
    saving.value = false
  }
}

const toggleEmployeeStatus = async (row) => {
  const nextStatus = row.status === 'active' ? 'inactive' : 'active'
  const previousStatus = row.status
  switchingEmployeeId.value = row.id
  employeeRows.value = employeeRows.value.map((employee) => (
    employee.id === row.id ? { ...employee, status: nextStatus } : employee
  ))
  try {
    await employeesApi.update(row.id, { status: nextStatus })
    ElMessage.success(nextStatus === 'active' ? '员工已启用' : '员工已停用')
    await loadEmployees()
  } catch (error) {
    employeeRows.value = employeeRows.value.map((employee) => (
      employee.id === row.id ? { ...employee, status: previousStatus } : employee
    ))
    ElMessage.error(getApiErrorMessage(error, '员工状态更新失败'))
  } finally {
    switchingEmployeeId.value = null
  }
}

const deleteEmployee = async (row) => {
  try {
    await ElMessageBox.confirm(`确认删除员工 ${row.name || row.employeeNo}？相关人脸特征也会被删除。`, '删除员工', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
    })
  } catch (error) {
    return
  }

  switchingEmployeeId.value = row.id
  try {
    await employeesApi.remove(row.id)
    ElMessage.success('员工已删除')
    await loadEmployees()
  } catch (error) {
    ElMessage.error(getApiErrorMessage(error, '员工删除失败'))
  } finally {
    switchingEmployeeId.value = null
  }
}

const getApiErrorMessage = (error, fallback) => {
  const response = error?.response?.data
  if (!response) return fallback
  if (response.message && response.message !== '请求参数错误') return response.message

  const detail = response.data
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) return detail.join('；')
  if (detail && typeof detail === 'object') {
    return Object.entries(detail)
      .map(([field, messages]) => `${field}: ${Array.isArray(messages) ? messages.join('；') : messages}`)
      .join('；')
  }

  return response.message || fallback
}

const captureCameraShot = (key) => {
  if (!activeVideoRef.value || !canvasRef.value) return

  const video = activeVideoRef.value
  const canvas = canvasRef.value
  canvas.width = video.videoWidth || 960
  canvas.height = video.videoHeight || 720
  const context = canvas.getContext('2d')
  context.drawImage(video, 0, 0, canvas.width, canvas.height)
  faceImages[key] = canvas.toDataURL('image/jpeg', 0.9)
  faceDirty[key] = true
  stopCamera()
}

const submitFace = async () => {
  if (!currentEmployee.value?.id) {
    ElMessage.warning('请先选择员工')
    return
  }

  const missingShot = !hasSavedFaces.value
    ? faceShotTypes.find((item) => !faceImages[item.key])
    : null
  if (missingShot) {
    ElMessage.warning(`请先录入${missingShot.label}照片`)
    return
  }
  if (hasSavedFaces.value && !hasDirtyFaces.value) {
    ElMessage.warning('请先拍摄或上传需要更新的人脸照片')
    return
  }

  enrolling.value = true
  try {
    const extractedFaces = []
    const pendingShots = faceShotTypes.filter((item) => faceDirty[item.key])
    for (const item of pendingShots) {
      const response = await aiServiceApi.extractFace({
        imageBase64: faceImages[item.key],
        requireSingleFace: true,
      })
      const data = response.data?.data || {}
      extractedFaces.push({
        faceType: item.key,
        imageBase64: faceImages[item.key],
        featureVector: data.featureVector,
        dimension: data.dimension,
      })
    }
    await faceApi.enroll({
      employeeId: currentEmployee.value.id,
      faces: extractedFaces,
    })
    try {
      await aiServiceApi.reloadCache({ source: 'backend' })
    } catch (cacheError) {
      console.warn('AIService face cache reload failed', cacheError)
    }
    ElMessage.success('人脸录入已提交')
    await refreshEmployeeFaces()
  } catch (error) {
    ElMessage.error(getApiErrorMessage(error, '人脸录入接口暂不可用'))
  } finally {
    enrolling.value = false
  }
}

onMounted(() => {
  loadEmployees()
})
</script>

<template>
  <div class="page-grid">
    <div class="panel table-panel">
      <SectionHeader title="员工管理">
        <el-button type="primary" @click="openCreateDialog">新增员工</el-button>
      </SectionHeader>
      <div class="filter-row">
        <el-input v-model="filters.keyword" placeholder="搜索姓名 / 工号" clearable @keyup.enter="queryEmployees" />
        <el-select v-model="filters.department" placeholder="部门" clearable>
          <el-option v-for="department in departmentOptions" :key="department" :label="department" :value="department" />
        </el-select>
        <el-select v-model="filters.status" placeholder="状态" clearable>
          <el-option label="在职" value="active" />
          <el-option label="停用" value="inactive" />
        </el-select>
        <el-button type="primary" @click="queryEmployees">查询</el-button>
      </div>
      <el-table v-loading="loading" :data="employeeRows" stripe>
        <el-table-column prop="employeeNo" label="工号" width="110" />
        <el-table-column prop="name" label="姓名" width="120" />
        <el-table-column prop="department" label="部门" width="130" />
        <el-table-column prop="position" label="岗位" min-width="140" />
        <el-table-column prop="phone" label="电话" min-width="150" />
        <el-table-column label="状态" width="100"><template #default="{ row }"><StatusTag :value="row.status" /></template></el-table-column>
        <el-table-column label="人脸录入" min-width="150">
          <template #default="{ row }">
            <div class="face-table-actions">
              <el-button link type="primary" @click="openFaceDialog(row)">
                {{ getEmployeeFaceButtonLabel(row) }}
              </el-button>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="210">
          <template #default="{ row }">
            <el-button link type="primary" @click="openEditDialog(row)">编辑</el-button>
            <el-button link type="warning" :loading="switchingEmployeeId === row.id" @click="toggleEmployeeStatus(row)">
              {{ row.status === 'active' ? '停用' : '启用' }}
            </el-button>
            <el-button link type="danger" :loading="switchingEmployeeId === row.id" @click="deleteEmployee(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <div class="record-count">共 {{ employeeTotal }} 条员工记录</div>
    </div>

    <el-dialog v-model="dialogVisible" title="新增员工" width="520px">
      <el-form label-position="top" :model="employeeForm">
        <el-form-item label="工号" required>
          <el-input v-model="employeeForm.employeeNo" placeholder="E004" />
        </el-form-item>
        <el-form-item label="姓名" required>
          <el-input v-model="employeeForm.name" placeholder="请输入姓名" />
        </el-form-item>
        <el-form-item label="部门">
          <el-input v-model="employeeForm.department" placeholder="请输入部门" />
        </el-form-item>
        <el-form-item label="职位">
          <el-input v-model="employeeForm.position" placeholder="请输入职位" />
        </el-form-item>
        <el-form-item label="电话号码">
          <el-input v-model="employeeForm.phone" placeholder="请输入电话号码" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitEmployee">保存员工</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="editDialogVisible" title="编辑员工信息" width="560px">
      <el-form label-position="top" :model="editForm" class="edit-employee-form">
        <el-form-item label="工号">
          <el-input v-model="editForm.employeeNo" disabled />
        </el-form-item>
        <el-form-item label="姓名">
          <el-input v-model="editForm.name" placeholder="请输入姓名" />
        </el-form-item>
        <el-form-item label="部门">
          <el-input v-model="editForm.department" placeholder="请输入部门" />
        </el-form-item>
        <el-form-item label="职位">
          <el-input v-model="editForm.position" placeholder="请输入职位" />
        </el-form-item>
        <el-form-item label="电话号码">
          <el-input v-model="editForm.phone" placeholder="请输入电话号码" />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="editForm.status" placeholder="请选择状态">
            <el-option label="在职" value="active" />
            <el-option label="停用" value="inactive" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitEmployeeEdit">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="faceDialogVisible"
      :title="faceDialogTitle"
      width="860px"
      class="face-enroll-dialog"
    >
      <div class="face-enroll">
        <div class="face-enroll__target">
          <div>
            <span>当前员工</span>
            <strong>{{ currentEmployee?.employeeNo || '待保存' }} {{ currentEmployee?.name || '' }}</strong>
            <el-tag v-if="!currentEmployee?.id" type="warning" size="small">需先保存员工</el-tag>
            <el-tag v-else-if="hasSavedFaces" size="small" type="info">展示最新录入照片</el-tag>
          </div>
          <el-button
            v-if="currentEmployee?.id"
            size="small"
            :loading="faceListLoading"
            @click="refreshEmployeeFaces"
          >
            刷新
          </el-button>
        </div>

        <div v-loading="faceListLoading" class="face-shot-grid">
          <div v-for="item in faceShotTypes" :key="item.key" class="face-shot-card">
            <div class="face-shot-card__head">
              <strong>{{ item.label }}</strong>
              <span v-if="getSavedFace(item.key) && !faceDirty[item.key]">已录入</span>
              <span v-else>{{ item.hint }}</span>
            </div>

            <button type="button" class="face-shot-window" @click="startCameraFor(item.key)">
              <video
                v-if="activeCameraKey === item.key"
                :ref="setActiveVideoRef"
                muted
                playsinline
                autoplay
              />
              <img v-else-if="faceImages[item.key]" :src="faceImages[item.key]" :alt="`${item.label}照片`" />
              <span v-else class="face-shot-empty">
                <b>+</b>
                <small>{{ item.label }}照片</small>
              </span>
              <i v-if="activeCameraKey === item.key || faceImages[item.key]" class="face-shot-guide"></i>
            </button>

            <input
              :ref="(element) => setFileInputRef(item.key, element)"
              class="face-file-input"
              type="file"
              accept="image/*"
              capture="user"
              @change="handleFaceFile($event, item.key)"
            />

            <div class="face-shot-actions">
              <el-button
                v-if="activeCameraKey === item.key"
                size="small"
                type="primary"
                @click="captureCameraShot(item.key)"
              >
                拍下
              </el-button>
              <el-button
                v-else
                size="small"
                type="primary"
                plain
                @click="startCameraFor(item.key)"
              >
                拍摄
              </el-button>
              <el-button
                v-if="activeCameraKey === item.key"
                size="small"
                @click="stopCamera"
              >
                取消拍摄
              </el-button>
              <el-button
                v-else
                size="small"
                @click="openFilePicker(item.key)"
              >
                上传
              </el-button>
              <el-button
                size="small"
                :type="getSavedFace(item.key) && !faceDirty[item.key] ? 'danger' : undefined"
                :plain="Boolean(getSavedFace(item.key) && !faceDirty[item.key])"
                :disabled="isFaceActionDisabled(item.key)"
                :loading="deletingFaceId === getSavedFace(item.key)?.id"
                @click="handleFaceSlotAction(item.key)"
              >
                {{ getFaceActionLabel(item.key) }}
              </el-button>
            </div>
          </div>
        </div>
        <canvas ref="canvasRef" class="capture-canvas"></canvas>
      </div>
      <template #footer>
        <el-button @click="closeFaceDialog">取消</el-button>
        <el-button
          type="primary"
          :loading="enrolling"
          :disabled="!currentEmployee?.id || (!hasSavedFaces && faceShotTypes.some((item) => !faceImages[item.key])) || (hasSavedFaces && !hasDirtyFaces)"
          @click="submitFace"
        >
          提交录入
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>
