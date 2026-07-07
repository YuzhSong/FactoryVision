<script setup>
import { ref } from 'vue'
import SectionHeader from '../components/SectionHeader.vue'
import StatusTag from '../components/StatusTag.vue'
import { employees } from '../data/placeholders'

const dialogVisible = ref(false)
</script>

<template>
  <div class="page-grid">
    <div class="panel table-panel">
      <SectionHeader title="员工管理" description="员工档案与人脸录入接口 planned，当前保留页面和表单入口。">
        <el-button type="primary" @click="dialogVisible = true">新增员工</el-button>
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
        <el-table-column label="状态" width="100"><template #default="{ row }"><StatusTag :value="row.status" /></template></el-table-column>
        <el-table-column label="人脸录入" min-width="150">
          <template #default><el-button link type="primary">录入占位</el-button></template>
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
      <el-form label-position="top">
        <el-form-item label="工号"><el-input placeholder="E004" /></el-form-item>
        <el-form-item label="姓名"><el-input placeholder="请输入姓名" /></el-form-item>
        <el-form-item label="部门"><el-input placeholder="请输入部门" /></el-form-item>
        <el-form-item label="人脸图片">
          <el-upload drag action="#" :auto-upload="false">
            <el-empty description="人脸录入接口 planned" />
          </el-upload>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary">保存占位</el-button>
      </template>
    </el-dialog>
  </div>
</template>
