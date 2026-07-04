<template>
  <div class="browser-page">
    <div class="page-header">
      <h2>Image Browser</h2>
      <div class="header-actions">
        <el-input
          v-model="searchQuery"
          placeholder="Search..."
          :prefix-icon="'Search'"
          clearable
          style="width:200px"
          @clear="fetchImages"
          @keyup.enter="fetchImages"
        />
        <el-radio-group v-model="viewMode">
          <el-radio-button value="grid">
            <el-icon><Grid /></el-icon>
          </el-radio-button>
          <el-radio-button value="masonry">
            <el-icon><DataAnalysis /></el-icon>
          </el-radio-button>
        </el-radio-group>
        <el-button
          v-if="selectedIds.length > 0"
          type="danger"
          :icon="'Delete'"
          @click="batchDelete"
        >
          Delete ({{ selectedIds.length }})
        </el-button>
      </div>
    </div>

    <div
      v-if="viewMode === 'grid'"
      class="grid-view"
      v-loading="loading"
    >
      <div
        v-for="item in images"
        :key="item.id"
        class="image-card"
        :class="{ selected: selectedIds.includes(item.id) }"
        @click="toggleSelect(item)"
      >
        <img :src="item.image_path" :alt="item.prompt" loading="lazy" />
        <div class="image-overlay">
          <el-checkbox
            v-model="item._selected"
            @click.stop
            @change="toggleSelect(item)"
          />
          <el-button
            size="small"
            circle
            :icon="'FullScreen'"
            @click.stop="openPreview(item)"
          />
        </div>
        <div class="image-info">
          <p class="image-prompt">{{ truncate(item.prompt, 30) }}</p>
          <p class="image-meta">{{ item.model?.split('/').pop() || 'default' }} · {{ item.width }}x{{ item.height }} · seed: {{ item.seed }}</p>
        </div>
      </div>

      <div v-if="!loading && images.length === 0" class="empty-state">
        <el-empty description="No images found" />
      </div>
    </div>

    <div
      v-if="viewMode === 'masonry'"
      class="masonry-view"
      v-loading="loading"
    >
      <div
        v-for="(item, idx) in images"
        :key="item.id"
        class="masonry-item"
        :style="{ height: getMasonryHeight(idx) + 'px' }"
        @click="openPreview(item)"
      >
        <img :src="item.image_path" :alt="item.prompt" loading="lazy" />
      </div>

      <div v-if="!loading && images.length === 0" class="empty-state">
        <el-empty description="No images found" />
      </div>
    </div>

    <el-dialog v-model="previewVisible" width="60%" top="5vh" destroy-on-close>
      <div v-if="previewItem">
        <img :src="previewItem.image_path" style="width:100%;border-radius:8px" />
        <div style="margin-top:12px">
          <p><strong>Prompt:</strong> {{ previewItem.prompt }}</p>
          <p><strong>Model:</strong> {{ previewItem.model || 'default' }} · <strong>Seed:</strong> {{ previewItem.seed }} · <strong>Size:</strong> {{ previewItem.width }}x{{ previewItem.height }}</p>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Grid, DataAnalysis } from '@element-plus/icons-vue'
import api from '@/api'

const images = ref([])
const loading = ref(false)
const searchQuery = ref('')
const viewMode = ref('grid')
const selectedIds = ref([])
const previewVisible = ref(false)
const previewItem = ref(null)

onMounted(() => fetchImages())

async function fetchImages() {
  loading.value = true
  try {
    const res = await api.get('/api/images', {
      params: { search: searchQuery.value || undefined, page_size: 100 },
    })
    images.value = (res.data || []).map(i => ({ ...i, _selected: false }))
  } catch (e) {
    ElMessage.error('Failed to fetch images')
  } finally {
    loading.value = false
  }
}

function toggleSelect(item) {
  item._selected = !item._selected
  if (item._selected) {
    selectedIds.value.push(item.id)
  } else {
    selectedIds.value = selectedIds.value.filter(id => id !== item.id)
  }
}

async function batchDelete() {
  try {
    await ElMessageBox.confirm(`Delete ${selectedIds.value.length} images?`, 'Confirm')
    await api.delete('/api/images', { data: selectedIds.value })
    images.value = images.value.filter(i => !selectedIds.value.includes(i.id))
    selectedIds.value = []
    ElMessage.success('Deleted')
  } catch (e) {
    if (e !== 'cancel') ElMessage.error('Failed to delete')
  }
}

function openPreview(item) {
  previewItem.value = item
  previewVisible.value = true
}

function getMasonryHeight(idx) {
  return 200 + (idx % 7) * 30
}

function truncate(str, len) {
  return str?.length > len ? str.slice(0, len) + '...' : str
}
</script>

<style scoped>
.browser-page {
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

.grid-view {
  flex: 1;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 12px;
  overflow-y: auto;
  align-content: start;
  align-items: start;
}

.image-card {
  border-radius: 8px;
  overflow: hidden;
  border: 2px solid transparent;
  cursor: pointer;
  position: relative;
  background: var(--bg-secondary);
  transition: border-color 0.2s;
  width: 100%;
}

.image-card.selected {
  border-color: #409eff;
}

.image-card img {
  width: 100%;
  aspect-ratio: 1;
  object-fit: cover;
  display: block;
  max-height: 280px;
}

.image-overlay {
  position: absolute;
  top: 8px;
  left: 8px;
  right: 8px;
  display: flex;
  justify-content: space-between;
  opacity: 0;
  transition: opacity 0.2s;
}

.image-card:hover .image-overlay {
  opacity: 1;
}

.image-info {
  padding: 6px 8px;
}

.image-prompt {
  font-size: 12px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.image-meta {
  font-size: 11px;
  color: var(--text-secondary);
}

.masonry-view {
  flex: 1;
  columns: 4;
  column-gap: 12px;
  overflow-y: auto;
}

.masonry-item {
  break-inside: avoid;
  margin-bottom: 12px;
  border-radius: 8px;
  overflow: hidden;
  cursor: pointer;
}

.masonry-item img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.empty-state {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 300px;
}
</style>
