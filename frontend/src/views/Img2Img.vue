<template>
  <div class="img2img">
    <div class="workspace">
      <div class="input-panel">
        <div class="panel-header">
          <h2>Image to Image</h2>
        </div>

        <div
          class="upload-area"
          @drop.prevent="handleDrop"
          @dragover.prevent
          @click="triggerUpload"
        >
          <template v-if="!uploadedImage">
            <el-icon :size="40"><Upload /></el-icon>
            <p>Drag & drop image here or click to upload</p>
          </template>
          <template v-else>
            <img :src="uploadedImage" class="upload-preview" />
            <div class="upload-overlay">
              <el-button size="small" @click.stop="uploadedImage = ''; inputRef.value = ''">
                Remove
              </el-button>
            </div>
          </template>
        </div>
        <input
          ref="fileInput"
          type="file"
          accept="image/*"
          style="display:none"
          @change="handleFile"
        />

        <el-form label-position="top" size="small">
          <el-form-item label="Strength">
            <el-slider
              v-model="strength"
              :min="0.1"
              :max="1"
              :step="0.05"
              show-input
              :input-size="'small'"
            />
          </el-form-item>
        </el-form>

        <el-input
          v-model="prompt"
          type="textarea"
          :rows="4"
          placeholder="Describe the changes you want..."
          class="prompt-input"
        />

        <ParameterPanel
          :params="params"
          :models="models"
          :show-batch="false"
        />

        <div class="action-bar">
          <el-button
            type="primary"
            size="large"
            :icon="VideoPlay"
            :loading="generating"
            @click="generate"
            class="generate-btn"
          >
            {{ generating ? 'Generating...' : 'Generate' }}
          </el-button>
        </div>
      </div>

      <div class="preview-panel">
        <ImagePreview
          :src="resultImage"
          :loading="generating"
          @preview="showFullPreview = true"
        />
      </div>
    </div>

    <el-dialog v-model="showFullPreview" width="80%" top="5vh">
      <img :src="resultImage" style="width:100%;border-radius:8px" />
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { VideoPlay, Upload } from '@element-plus/icons-vue'
import api from '@/api'
import { useAppStore } from '@/stores/app'
import ImagePreview from '@/components/ImagePreview.vue'
import ParameterPanel from '@/components/ParameterPanel.vue'

const appStore = useAppStore()
const fileInput = ref(null)

const prompt = ref('')
const strength = ref(0.8)
const uploadedImage = ref('')
const uploadedPath = ref('')
const generating = ref(false)
const resultImage = ref('')
const showFullPreview = ref(false)
const models = ref([])

const params = reactive({
  width: 1024,
  height: 1024,
  steps: 4,
  guidance: 3.5,
  seed: null,
  model: '',
})

onMounted(async () => {
  try {
    const res = await api.get('/api/models')
    models.value = res.data || []
  } catch (e) {}
})

function triggerUpload() {
  fileInput.value?.click()
}

async function handleFile(e) {
  const file = e.target.files?.[0]
  if (file) await uploadFile(file)
}

async function handleDrop(e) {
  const file = e.dataTransfer.files?.[0]
  if (file) await uploadFile(file)
}

async function uploadFile(file) {
  const form = new FormData()
  form.append('file', file)

  try {
    const res = await api.post('/api/upload', form)
    uploadedPath.value = res.data.path
    uploadedImage.value = res.data.url
    ElMessage.success('Image uploaded')
  } catch (e) {
    ElMessage.error('Upload failed')
  }
}

async function generate() {
  if (!uploadedPath.value) {
    ElMessage.warning('Please upload an image first')
    return
  }
  if (!prompt.value.trim()) {
    ElMessage.warning('Please enter a prompt')
    return
  }

  generating.value = true
  resultImage.value = ''

  try {
    const res = await api.post('/api/generate/img2img', {
      prompt: prompt.value,
      model: params.model,
      steps: params.steps,
      guidance: params.guidance,
      seed: params.seed || undefined,
      strength: strength.value,
      image_path: uploadedPath.value,
    })

    appStore.fetchTasks()
    ElMessage.success('Task queued')
    appStore.currentTaskId = res.data.task_id
  } catch (e) {
    ElMessage.error('Failed to queue task')
  } finally {
    generating.value = false
  }
}
</script>

<style scoped>
.img2img {
  height: 100%;
  padding: 20px;
}

.workspace {
  display: grid;
  grid-template-columns: 420px 1fr;
  gap: 20px;
  height: 100%;
}

.input-panel {
  background: var(--bg-secondary);
  border-radius: 12px;
  padding: 20px;
  border: 1px solid var(--border-color);
  overflow-y: auto;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.panel-header h2 {
  font-size: 18px;
  font-weight: 600;
}

.upload-area {
  border: 2px dashed var(--border-color);
  border-radius: 8px;
  padding: 30px;
  text-align: center;
  cursor: pointer;
  margin-bottom: 16px;
  position: relative;
  color: var(--text-secondary);
  transition: border-color 0.3s;
}

.upload-area:hover {
  border-color: #409eff;
}

.upload-preview {
  max-height: 150px;
  max-width: 100%;
  border-radius: 4px;
}

.upload-overlay {
  position: absolute;
  top: 8px;
  right: 8px;
}

.prompt-input {
  margin-bottom: 16px;
}

.action-bar {
  display: flex;
  gap: 12px;
  margin-top: 8px;
}

.generate-btn {
  flex: 1;
}

.preview-panel {
  background: var(--bg-secondary);
  border-radius: 12px;
  border: 1px solid var(--border-color);
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}
</style>
