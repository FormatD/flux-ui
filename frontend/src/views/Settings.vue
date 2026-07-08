<template>
  <div class="settings-page">
    <div class="page-header">
      <h2>Settings</h2>
    </div>

    <div class="settings-sections">
      <el-card class="settings-card">
        <template #header>
          <span>Generation Defaults</span>
        </template>
        <el-form :model="settings" label-position="left" label-width="140px">
          <el-form-item label="Default Model">
            <el-select v-model="settings.default_model" placeholder="Auto" clearable style="width:300px">
              <el-option
                v-for="m in models"
                :key="m.id"
                :label="m.name"
                :value="m.name"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="Default Width">
            <el-select v-model="settings.default_width" style="width:300px">
              <el-option label="512" :value="512" />
              <el-option label="768" :value="768" />
              <el-option label="1024" :value="1024" />
              <el-option label="1280" :value="1280" />
              <el-option label="1536" :value="1536" />
            </el-select>
          </el-form-item>
          <el-form-item label="Default Height">
            <el-select v-model="settings.default_height" style="width:300px">
              <el-option label="512" :value="512" />
              <el-option label="768" :value="768" />
              <el-option label="1024" :value="1024" />
              <el-option label="1280" :value="1280" />
              <el-option label="1536" :value="1536" />
            </el-select>
          </el-form-item>
          <el-form-item label="Default Steps">
            <el-input-number v-model="settings.default_steps" :min="1" :max="50" />
          </el-form-item>
          <el-form-item label="Default CFG">
            <el-input-number v-model="settings.default_cfg" :min="1" :max="20" :step="0.5" />
          </el-form-item>
        </el-form>
      </el-card>

      <el-card class="settings-card">
        <template #header>
          <span>Interface</span>
        </template>
        <el-form label-position="left" label-width="140px">
          <el-form-item label="Theme">
            <el-switch
              :model-value="appStore.darkMode"
              @update:model-value="appStore.toggleDark()"
              active-text="Dark"
              inactive-text="Light"
            />
          </el-form-item>
          <el-form-item label="Language">
            <el-select model-value="zh-CN" style="width:300px" disabled>
              <el-option label="Chinese (中文)" value="zh-CN" />
              <el-option label="English" value="en" />
            </el-select>
          </el-form-item>
        </el-form>
      </el-card>

      <el-card class="settings-card">
        <template #header>
          <span>Storage</span>
        </template>
        <el-form label-position="left" label-width="140px">
          <el-form-item label="Output Directory">
            <el-input v-model="settings.output_dir" style="width:300px" placeholder="./output" />
          </el-form-item>
          <el-form-item label="History Count">
            <el-input-number v-model="settings.history_count" :min="10" :max="1000" :step="10" />
          </el-form-item>
        </el-form>
      </el-card>

      <el-card class="settings-card">
        <template #header>
          <span>Backend</span>
        </template>
        <el-form label-position="left" label-width="140px">
          <el-form-item label="MLX Executable">
            <div style="display:flex;align-items:center;gap:8px">
              <el-input v-model="settings.mlux_executable_path" style="width:300px" placeholder="Auto-detect (PATH)" />
              <el-tooltip content="Custom path to the mflux CLI executable. Leave empty for auto-detection via PATH." placement="top">
                <el-icon><InfoFilled /></el-icon>
              </el-tooltip>
            </div>
          </el-form-item>
          <el-form-item label="Model Cache Dir">
            <div style="display:flex;align-items:center;gap:8px">
              <el-input v-model="settings.model_cache_dir" style="width:300px" placeholder="~/.cache/huggingface/hub" />
              <el-tooltip content="Directory where HuggingFace model files are cached." placement="top">
                <el-icon><InfoFilled /></el-icon>
              </el-tooltip>
            </div>
          </el-form-item>
          <el-form-item label="Output Directory">
            <div style="display:flex;align-items:center;gap:8px">
              <el-input v-model="settings.output_dir" style="width:300px" placeholder="./output" />
              <el-tooltip content="Directory where generated images are saved. Restart required after change." placement="top">
                <el-icon><InfoFilled /></el-icon>
              </el-tooltip>
            </div>
          </el-form-item>
          <el-form-item label="Upload Directory">
            <div style="display:flex;align-items:center;gap:8px">
              <el-input v-model="settings.upload_dir" style="width:300px" placeholder="./uploads" />
              <el-tooltip content="Directory where uploaded images are stored. Restart required after change." placement="top">
                <el-icon><InfoFilled /></el-icon>
              </el-tooltip>
            </div>
          </el-form-item>
          <el-form-item label="Scan Directories">
            <div style="display:flex;align-items:center;gap:8px">
              <el-input v-model="settings.model_scan_dirs" style="width:300px" placeholder="~/Models,~/Downloads/models" />
              <el-tooltip content="Comma-separated list of directories to scan for models." placement="top">
                <el-icon><InfoFilled /></el-icon>
              </el-tooltip>
            </div>
          </el-form-item>
        </el-form>
      </el-card>

      <div class="settings-actions">
        <el-button type="primary" @click="saveSettings" :loading="saving">Save Settings</el-button>
        <el-button @click="resetSettings">Reset</el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { InfoFilled } from '@element-plus/icons-vue'
import api from '@/api'
import { useAppStore } from '@/stores/app'

const appStore = useAppStore()
const models = ref([])
const saving = ref(false)

const settings = reactive({
  default_model: '',
  default_width: 1024,
  default_height: 1024,
  default_steps: 4,
  default_cfg: 3.5,
  output_dir: './output',
  history_count: 100,
  mlux_executable_path: '',
  model_cache_dir: '',
  upload_dir: '',
  model_scan_dirs: '',
})

onMounted(async () => {
  try {
    const res = await api.get('/api/models')
    models.value = res.data || []
  } catch (e) {}
  await loadSettings()
})

async function loadSettings() {
  try {
    const res = await api.get('/api/settings')
    if (res.data.default_width) settings.default_width = parseInt(res.data.default_width)
    if (res.data.default_height) settings.default_height = parseInt(res.data.default_height)
    if (res.data.default_steps) settings.default_steps = parseInt(res.data.default_steps)
    if (res.data.default_cfg) settings.default_cfg = parseFloat(res.data.default_cfg)
    if (res.data.default_model) settings.default_model = res.data.default_model
    if (res.data.output_dir) settings.output_dir = res.data.output_dir
    if (res.data.history_count) settings.history_count = parseInt(res.data.history_count)
    if (res.data.mlux_executable_path) settings.mlux_executable_path = res.data.mlux_executable_path
    if (res.data.model_cache_dir) settings.model_cache_dir = res.data.model_cache_dir
    if (res.data.upload_dir) settings.upload_dir = res.data.upload_dir
    if (res.data.model_scan_dirs) settings.model_scan_dirs = res.data.model_scan_dirs
  } catch (e) {}
}

async function saveSettings() {
  saving.value = true
  try {
    const entries = Object.entries(settings)
    for (const [key, value] of entries) {
      await api.post('/api/settings', { key, value: String(value) })
    }
    ElMessage.success('Settings saved')
  } catch (e) {
    ElMessage.error('Failed to save settings')
  } finally {
    saving.value = false
  }
}

function resetSettings() {
  settings.default_model = ''
  settings.default_width = 1024
  settings.default_height = 1024
  settings.default_steps = 4
  settings.default_cfg = 3.5
  settings.output_dir = './output'
  settings.history_count = 100
  settings.mlux_executable_path = ''
  settings.model_cache_dir = ''
  settings.upload_dir = ''
  settings.model_scan_dirs = ''
}
</script>

<style scoped>
.settings-page {
  padding: 20px;
  max-width: 800px;
}

.page-header {
  margin-bottom: 20px;
}

.page-header h2 {
  font-size: 18px;
  font-weight: 600;
}

.settings-sections {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.settings-card {
  border-radius: 8px;
}

.settings-actions {
  display: flex;
  gap: 12px;
  padding-top: 8px;
}
</style>
