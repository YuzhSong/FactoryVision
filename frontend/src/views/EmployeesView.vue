<script setup>
import { nextTick, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import SectionHeader from '../components/SectionHeader.vue'
import StatusTag from '../components/StatusTag.vue'
import { employees } from '../data/placeholders'
import { employeesApi, faceApi } from '../api/modules'

const dialogVisible = ref(false)
const faceDialogVisible = ref(false)
const saving = ref(false)
const enrolling = ref(false)
const cameraActive = ref(false)
const cameraError = ref('')
const capturedImage = ref('')
const currentEmployee = ref(null)
const videoRef = ref(null)
const canvasRef = ref(null)
let mediaStream = null

const employeeForm = reactive({
  employeeNo: '',
  name: '',
  department: '',
  position: '',
  phone: '',
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

    if (response?.data?.id) {
      currentEmployee.value = {
        id: response.data.id,
        employeeNo: employeeForm.employeeNo,
        name: employeeForm.name,
      }
      faceDialogVisible.value = true
    }
  } catch (error) {
    ElMessage.error(error?.response?.data?.message || '员工创建接口暂不可用')
  } finally {
    saving.value = false
  }
}

const stopCamera = () => {
  if (mediaStream) {
    mediaStream.getTracks().forEach((track) => track.stop())
    mediaStream = null
  }
  cameraActive.value = false
}

const startCamera = async () => {
  cameraError.value = ''
  capturedImage.value = ''

  if (!navigator.mediaDevices?.getUserMedia) {
    cameraError.value = '当前浏览器不支持摄像头录入'
    return
  }

  try {
    stopCamera()
    mediaStream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: 'user', width: { ideal: 960 }, height: { ideal: 720 } },
      audio: false,
    })
    await nextTick()
    if (videoRef.value) {
      videoRef.value.srcObject = mediaStream
      await videoRef.value.play()
    }
    cameraActive.value = true
  } catch (error) {
    cameraError.value = '无法打开摄像头，请检查浏览器权限'
  }
}

const captureFace = () => {
  if (!videoRef.value || !canvasRef.value) return

  const video = videoRef.value
  const canvas = canvasRef.value
  canvas.width = video.videoWidth || 960
  canvas.height = video.videoHeight || 720
  const context = canvas.getContext('2d')
  context.drawImage(video, 0, 0, canvas.width, canvas.height)
  capturedImage.value = canvas.toDataURL('image/jpeg', 0.9)
  stopCamera()
}

const openFaceDialog = (employee) => {
  currentEmployee.value = employee
  capturedImage.value = ''
  cameraError.value = ''
  faceDialogVisible.value = true
}

const closeFaceDialog = () => {
  stopCamera()
  faceDialogVisible.value = false
}

const submitFace = async () => {
  if (!currentEmployee.value?.id) {
    ElMessage.warning('请先选择员工')
    return
  }
  if (!capturedImage.value) {
    ElMessage.warning('请先拍摄人脸照片')
    return
  }

  enrolling.value = true
  try {
    await faceApi.enroll({
      employeeId: currentEmployee.value.id,
      imageBase64: capturedImage.value,
    })
    ElMessage.success('人脸录入已提交')
    closeFaceDialog()
  } catch (error) {
    ElMessage.error(error?.response?.data?.message || '人脸录入接口暂不可用')
  } finally {
    enrolling.value = false
  }
}
</script>

<template>
  <div class="page-grid">
    <div class="panel table-panel">
      <SectionHeader title="员工管理" description="员工档案与人脸录入接口 planned，当前保留页面和表单入口。">
        <el-button type="primary" @click="openCreateDialog">新增员工</el-button>
      </SectionHeader>
      <div class="filter-row">
        <el-input placeholder="搜索姓名 / 工号" clearable />
        <el-select placeholder="部门" clearable>
          <el-option label="生产部" value="生产部" />
          <el-option label="设备部" value="设备部" />
          <el-option label="仓储部" value="仓储部" />
        </el-select>
        <el-select placeholder="状态" clearable>
          <el-option label="在职" value="active" />
          <el-option label="停用" value="inactive" />
        </el-select>
        <el-button type="primary">查询</el-button>
      </div>
      <el-table :data="employees" stripe>
        <el-table-column prop="employeeNo" label="工号" width="110" />
        <el-table-column prop="name" label="姓名" width="120" />
        <el-table-column prop="department" label="部门" width="130" />
        <el-table-column prop="position" label="岗位" min-width="140" />
        <el-table-column prop="phone" label="电话" min-width="150" />
        <el-table-column label="状态" width="100"><template #default="{ row }"><StatusTag :value="row.status" /></template></el-table-column>
        <el-table-column label="人脸录入" min-width="150">
          <template #default="{ row }">
            <el-button link type="primary" @click="openFaceDialog(row)">开始录入</el-button>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150">
          <template #default>
            <el-button link type="primary">编辑</el-button>
            <el-button link type="danger">停用</el-button>
          </template>
        </el-table-column>
      </el-table>
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

    <el-dialog
      v-model="faceDialogVisible"
      title="人脸录入"
      width="680px"
      class="face-enroll-dialog"
      @closed="stopCamera"
    >
      <div class="face-enroll">
        <div class="face-enroll__target">
          <span>当前员工</span>
          <strong>{{ currentEmployee?.employeeNo || '待保存' }} {{ currentEmployee?.name || '' }}</strong>
          <el-tag v-if="!currentEmployee?.id" type="warning" size="small">需先保存员工</el-tag>
        </div>

        <div class="face-camera">
          <video v-show="cameraActive && !capturedImage" ref="videoRef" muted playsinline />
          <img v-if="capturedImage" :src="capturedImage" alt="已拍摄的人脸照片" />
          <div v-if="!cameraActive && !capturedImage" class="face-camera__empty">
            <span>摄像头未开启</span>
            <small>点击下方按钮后，工作人员可直接通过本机摄像头录入人脸。</small>
          </div>
          <div class="face-frame"></div>
        </div>

        <el-alert
          v-if="cameraError"
          :title="cameraError"
          type="warning"
          show-icon
          :closable="false"
        />

        <div class="face-actions">
          <el-button @click="startCamera">打开摄像头</el-button>
          <el-button type="primary" :disabled="!cameraActive" @click="captureFace">拍摄照片</el-button>
          <el-button :disabled="!capturedImage" @click="capturedImage = ''">重新拍摄</el-button>
        </div>
        <canvas ref="canvasRef" class="capture-canvas"></canvas>
      </div>
      <template #footer>
        <el-button @click="closeFaceDialog">取消</el-button>
        <el-button
          type="primary"
          :loading="enrolling"
          :disabled="!currentEmployee?.id || !capturedImage"
          @click="submitFace"
        >
          提交录入
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>
