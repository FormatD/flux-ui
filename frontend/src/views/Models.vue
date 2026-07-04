<template>
  <div class="models-page">
    <div class="page-header">
      <h2>Model Manager</h2>
      <el-button type="primary" :icon="'Refresh'" @click="scanModels" :loading="scanning">
        Scan Models
      </el-button>
    </div>

    <el-table :data="models" v-loading="loading" stripe style="width:100%">
      <el-table-column prop="name" label="Name" min-width="200" />
      <el-table-column prop="model_type" label="Type" width="100" />
      <el-table-column prop="quantization" label="Quantization" width="120" />
      <el-table-column label="Size" width="120">
        <template #default="{ row }">
          {{ formatSize(row.size_bytes) }}
        </template>
      </el-table-column>
      <el-table-column label="Default" width="100" align="center">
        <template #default="{ row }">
          <el-tag v-if="row.is_default" type="success" size="small">Default</el-tag>
          <el-button
            v-else
            size="small"
            text
            @click="setDefault(row)"
          >
            Set Default
          </el-button>
        </template>
      </el-table-column>
      <el-table-column label="Actions" width="100" align="center">
        <template #default="{ row }">
          <el-button size="small" type="danger" :icon="'Delete'" circle @click="deleteModel(row)" />
        </template>
      </el-table-column>
    </el-table>

    <div v-if="!loading && models.length === 0" class="empty-state">
      <el-empty description="No models found. Click 'Scan Models' to search." />
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '@/api'

const models = ref([])
const loading = ref(false)
const scanning = ref(false)

onMounted(() => fetchModels())

async function fetchModels() {
  loading.value = true
  try {
    const res = await api.get('/api/models')
    models.value = res.data || []
  } catch (e) {
    ElMessage.error('Failed to fetch models')
  } finally {
    loading.value = false
  }
}

async function scanModels() {
  scanning.value = true
  try {
    const res = await api.post('/api/models/scan')
    ElMessage.success(`Scanned ${res.data.scanned} models, ${res.data.added} new`)
    await fetchModels()
  } catch (e) {
    ElMessage.error('Failed to scan models')
  } finally {
    scanning.value = false
  }
}

async function setDefault(model) {
  try {
    await api.post(`/api/models/${model.id}/default`)
    models.value.forEach(m => m.is_default = false)
    model.is_default = true
    ElMessage.success(`Default model: ${model.name}`)
  } catch (e) {
    ElMessage.error('Failed to set default')
  }
}

async function deleteModel(model) {
  try {
    await ElMessageBox.confirm(`Delete model record '${model.name}'?`, 'Confirm')
    await api.delete(`/api/models/${model.id}`)
    models.value = models.value.filter(m => m.id !== model.id)
    ElMessage.success('Deleted')
  } catch (e) {
    if (e !== 'cancel') ElMessage.error('Failed to delete')
  }
}

function formatSize(bytes) {
  if (!bytes) return '-'
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  let i = 0
  let size = bytes
  while (size >= 1024 && i < units.length - 1) {
    size /= 1024
    i++
  }
  return `${size.toFixed(1)} ${units[i]}`
}
</script>

<style scoped>
.models-page {
  padding: 20px;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.page-header h2 {
  font-size: 18px;
  font-weight: 600;
}

.empty-state {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 300px;
  flex: 1;
}
</style>
