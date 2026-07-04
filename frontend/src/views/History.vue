<template>
  <div class="history-page">
    <div class="page-header">
      <h2>History</h2>
      <div class="header-actions">
        <el-input
          v-model="searchQuery"
          placeholder="Search prompts..."
          :prefix-icon="'Search'"
          clearable
          style="width:200px"
          @clear="fetchHistory"
          @keyup.enter="fetchHistory"
        />
        <el-checkbox v-model="showFavorites" @change="fetchHistory">
          Favorites only
        </el-checkbox>
      </div>
    </div>

    <div class="history-grid" v-loading="loading">
      <div
        v-for="item in records"
        :key="item.id"
        class="history-card"
        @click="openPreview(item)"
      >
        <div class="card-image">
          <img :src="item.image_path" :alt="item.prompt" loading="lazy" />
          <div class="card-overlay">
            <el-button
              size="small"
              :type="item.favorite ? 'warning' : 'default'"
              :icon="'Star'"
              circle
              @click.stop="toggleFavorite(item)"
            />
            <el-button
              size="small"
              type="danger"
              :icon="'Delete'"
              circle
              @click.stop="deleteRecord(item)"
            />
          </div>
        </div>
        <div class="card-info">
          <p class="card-prompt">{{ truncate(item.prompt, 50) }}</p>
          <div class="card-meta">
            <span>{{ item.model?.split('/').pop() || 'default' }}</span>
            <span>{{ item.width }}x{{ item.height }}</span>
            <span>seed: {{ item.seed }}</span>
          </div>
        </div>
      </div>

      <div v-if="!loading && records.length === 0" class="empty-state">
        <el-empty description="No images yet" />
      </div>
    </div>

    <div class="pagination-wrap" v-if="total > pageSize">
      <el-pagination
        v-model:current-page="page"
        :page-size="pageSize"
        :total="total"
        layout="prev, pager, next"
        @current-change="fetchHistory"
      />
    </div>

    <el-dialog v-model="previewVisible" width="70%" top="5vh" destroy-on-close>
      <div class="preview-content" v-if="previewItem">
        <img :src="previewItem.image_path" class="preview-image" />
        <div class="preview-details">
          <el-descriptions :column="2" border size="small">
            <el-descriptions-item label="Prompt">{{ previewItem.prompt }}</el-descriptions-item>
            <el-descriptions-item label="Negative">{{ previewItem.negative_prompt || '-' }}</el-descriptions-item>
            <el-descriptions-item label="Seed">{{ previewItem.seed }}</el-descriptions-item>
            <el-descriptions-item label="Model">{{ previewItem.model || 'default' }}</el-descriptions-item>
            <el-descriptions-item label="Size">{{ previewItem.width }}x{{ previewItem.height }}</el-descriptions-item>
            <el-descriptions-item label="Steps">{{ previewItem.steps }}</el-descriptions-item>
            <el-descriptions-item label="CFG">{{ previewItem.guidance }}</el-descriptions-item>
            <el-descriptions-item label="Time">{{ formatTime(previewItem.create_time) }}</el-descriptions-item>
          </el-descriptions>
          <div class="preview-actions">
            <el-button type="primary" :icon="'VideoPlay'" @click="regenerate(previewItem)">
              Regenerate
            </el-button>
            <el-button :icon="'Download'" @click="downloadImage(previewItem)">
              Download
            </el-button>
            <el-button :icon="'CopyDocument'" @click="copyParams(previewItem)">
              Copy Params
            </el-button>
          </div>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '@/api'

const records = ref([])
const loading = ref(false)
const searchQuery = ref('')
const showFavorites = ref(false)
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const previewVisible = ref(false)
const previewItem = ref(null)

onMounted(() => fetchHistory())

async function fetchHistory() {
  loading.value = true
  try {
    const res = await api.get('/api/images', {
      params: {
        page: page.value,
        page_size: pageSize.value,
        search: searchQuery.value || undefined,
        favorite: showFavorites.value || undefined,
      },
    })
    records.value = res.data || []
    total.value = parseInt(res.headers?.['x-total-count'] || res.data?.length || 0)
  } catch (e) {
    ElMessage.error('Failed to fetch history')
  } finally {
    loading.value = false
  }
}

async function toggleFavorite(item) {
  try {
    await api.patch(`/api/images/${item.id}`, { favorite: !item.favorite })
    item.favorite = !item.favorite
  } catch (e) {
    ElMessage.error('Failed to update')
  }
}

async function deleteRecord(item) {
  try {
    await ElMessageBox.confirm('Delete this image?', 'Confirm')
    await api.delete(`/api/images/${item.id}`)
    records.value = records.value.filter(r => r.id !== item.id)
    ElMessage.success('Deleted')
  } catch (e) {
    if (e !== 'cancel') ElMessage.error('Failed to delete')
  }
}

function openPreview(item) {
  previewItem.value = item
  previewVisible.value = true
}

function regenerate(item) {
  previewVisible.value = false
}

function downloadImage(item) {
  const a = document.createElement('a')
  a.href = item.image_path
  a.download = `mflux_${item.id}.png`
  a.click()
}

function copyParams(item) {
  const text = `prompt: ${item.prompt}\nseed: ${item.seed}\nmodel: ${item.model || 'default'}\nsteps: ${item.steps}\ncfg: ${item.guidance}\nsize: ${item.width}x${item.height}`
  navigator.clipboard.writeText(text)
  ElMessage.success('Copied')
}

function truncate(str, len) {
  return str?.length > len ? str.slice(0, len) + '...' : str
}

function formatTime(t) {
  if (!t) return '-'
  return new Date(t).toLocaleString()
}
</script>

<style scoped>
.history-page {
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

.header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.history-grid {
  flex: 1;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 16px;
  overflow-y: auto;
  padding-bottom: 20px;
  align-content: start;
  align-items: start;
}

.history-card {
  background: var(--bg-secondary);
  border-radius: 8px;
  border: 1px solid var(--border-color);
  overflow: hidden;
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s;
  width: 100%;
}

.history-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0,0,0,0.1);
}

.card-image {
  position: relative;
  aspect-ratio: 1;
  overflow: hidden;
  max-height: 280px;
}

.card-image img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.card-overlay {
  position: absolute;
  top: 8px;
  right: 8px;
  display: flex;
  gap: 4px;
  opacity: 0;
  transition: opacity 0.2s;
}

.history-card:hover .card-overlay {
  opacity: 1;
}

.card-info {
  padding: 8px 12px;
}

.card-prompt {
  font-size: 12px;
  color: var(--text-primary);
  margin-bottom: 4px;
}

.card-meta {
  display: flex;
  gap: 8px;
  font-size: 11px;
  color: var(--text-secondary);
}

.empty-state {
  grid-column: 1 / -1;
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 300px;
}

.pagination-wrap {
  display: flex;
  justify-content: center;
  padding: 16px 0;
}

.preview-content {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}

.preview-image {
  width: 100%;
  border-radius: 8px;
}

.preview-details {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.preview-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
</style>
