<template>
  <div class="text2img">
    <div class="workspace">
      <div class="input-panel">
        <div class="panel-header">
          <h2>Text to Image</h2>
          <el-button
            :icon="MagicStick"
            type="primary"
            @click="showEnhancer = true"
            size="small"
          >
            Enhance
          </el-button>
        </div>

        <el-input
          v-model="prompt"
          type="textarea"
          :rows="4"
          placeholder="Describe the image you want to generate..."
          class="prompt-input"
        />

        <el-input
          v-model="negativePrompt"
          type="textarea"
          :rows="2"
          placeholder="Negative prompt (optional)"
          class="neg-prompt-input"
          size="small"
        />

        <ParameterPanel
          :params="params"
          :models="models"
          @update:params="params = $event"
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
          <el-button
            size="large"
            :icon="Delete"
            @click="clear"
          >
            Clear
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

    <el-dialog v-model="showEnhancer" title="AI Prompt Enhancer" width="500px">
      <el-input
        v-model="enhanceInput"
        type="textarea"
        :rows="3"
        placeholder="Enter your prompt idea..."
      />
      <div style="margin:12px 0">
        <el-select v-model="enhanceStyle" style="width:100%">
          <el-option label="Enhance" value="enhance" />
          <el-option label="Realistic" value="realistic" />
          <el-option label="Anime" value="anime" />
          <el-option label="Cinematic" value="cinematic" />
        </el-select>
      </div>
      <template #footer>
        <el-button @click="showEnhancer = false">Cancel</el-button>
        <el-button type="primary" @click="applyEnhance" :loading="enhancing">
          Apply
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { VideoPlay, Delete, MagicStick } from '@element-plus/icons-vue'
import api from '@/api'
import { useAppStore } from '@/stores/app'
import ImagePreview from '@/components/ImagePreview.vue'
import ParameterPanel from '@/components/ParameterPanel.vue'

const appStore = useAppStore()

const prompt = ref('')
const negativePrompt = ref('')
const generating = ref(false)
const resultImage = ref('')
const showFullPreview = ref(false)
const showEnhancer = ref(false)
const enhanceInput = ref('')
const enhanceStyle = ref('enhance')
const enhancing = ref(false)
const models = ref([])

const params = reactive({
  width: 1024,
  height: 1024,
  steps: 4,
  guidance: 3.5,
  seed: null,
  batch_count: 1,
  model: '',
})

onMounted(async () => {
  try {
    const res = await api.get('/api/models')
    models.value = res.data || []
  } catch (e) {}
})

async function generate() {
  if (!prompt.value.trim()) {
    ElMessage.warning('Please enter a prompt')
    return
  }

  generating.value = true
  resultImage.value = ''

  try {
    const res = await api.post('/api/generate/text2img', {
      prompt: prompt.value,
      negative_prompt: negativePrompt.value,
      steps: params.steps,
      guidance: params.guidance,
      seed: params.seed || undefined,
      width: params.width,
      height: params.height,
      batch_count: params.batch_count,
      model: params.model,
    })

    appStore.fetchTasks()
    ElMessage.success('Task queued')

    appStore.currentTaskId = res.data.task_id

    // Poll for completion
    const poll = setInterval(async () => {
      try {
        const r = await api.get(`/api/tasks/${res.data.task_id}`)
        const task = r.data
        if (task.status === 'completed') {
          clearInterval(poll)
          generating.value = false
          appStore.fetchTasks()
          if (task.result_path) {
            resultImage.value = task.result_path
            ElMessage.success('Image generated!')
          }
        } else if (task.status === 'failed') {
          clearInterval(poll)
          generating.value = false
          ElMessage.error(`Generation failed: ${task.error || 'Unknown error'}`)
        }
      } catch (e) {
        // ignore polling errors
      }
    }, 2000)
  } catch (e) {
    ElMessage.error('Failed to queue task')
  } finally {
    generating.value = false
  }
}

function clear() {
  prompt.value = ''
  negativePrompt.value = ''
  resultImage.value = ''
  params.seed = null
}

async function applyEnhance() {
  if (!enhanceInput.value.trim()) return
  enhancing.value = true
  try {
    const res = await api.post('/api/prompts/enhance', {
      prompt: enhanceInput.value,
      style: enhanceStyle.value,
      language: 'en',
    })
    prompt.value = res.data.enhanced
    showEnhancer.value = false
    ElMessage.success('Prompt enhanced')
  } catch (e) {
    ElMessage.error('Failed to enhance prompt')
  } finally {
    enhancing.value = false
  }
}
</script>

<style scoped>
.text2img {
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

.prompt-input {
  margin-bottom: 12px;
}

.neg-prompt-input {
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
