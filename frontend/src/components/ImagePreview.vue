<template>
  <div class="image-preview" v-loading="loading">
    <div v-if="!src && !loading" class="preview-placeholder">
      <el-icon :size="48"><Picture /></el-icon>
      <p>Generated image will appear here</p>
    </div>
    <img v-if="src" :src="src" alt="Generated" @click="$emit('preview', src)" />
    <div v-if="taskData" class="preview-overlay">
      <div class="overlay-info">
        <span>{{ taskData.prompt }}</span>
        <span>{{ taskData.seed }}</span>
        <span>{{ taskData.model }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  src: String,
  loading: Boolean,
  taskData: Object,
})

defineEmits(['preview'])
</script>

<style scoped>
.image-preview {
  width: 100%;
  height: 100%;
  min-height: 400px;
  border-radius: 12px;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  position: relative;
}

.preview-placeholder {
  text-align: center;
  color: var(--text-secondary);
}

.preview-placeholder p {
  margin-top: 12px;
  font-size: 14px;
}

.image-preview img {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
  cursor: pointer;
}

.preview-overlay {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  background: rgba(0,0,0,0.6);
  color: #fff;
  padding: 8px 12px;
  font-size: 12px;
}

.overlay-info {
  display: flex;
  gap: 16px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
