<template>
  <div class="prompts-page">
    <div class="page-header">
      <h2>Prompt Manager</h2>
      <el-button type="primary" :icon="'Plus'" @click="openEditor()">New Prompt</el-button>
    </div>

    <div class="category-tabs">
      <el-radio-group v-model="activeCategory" @change="fetchPrompts">
        <el-radio-button label="">All</el-radio-button>
        <el-radio-button label="realistic">Realistic</el-radio-button>
        <el-radio-button label="anime">Anime</el-radio-button>
        <el-radio-button label="landscape">Landscape</el-radio-button>
        <el-radio-button label="portrait">Portrait</el-radio-button>
        <el-radio-button label="custom">Custom</el-radio-button>
      </el-radio-group>
    </div>

    <div class="prompts-grid" v-loading="loading">
      <div
        v-for="p in prompts"
        :key="p.id"
        class="prompt-card"
      >
        <div class="prompt-card-header">
          <span class="prompt-title">{{ p.title }}</span>
          <div class="prompt-card-actions">
            <el-button
              size="small"
              :type="p.favorite ? 'warning' : 'default'"
              :icon="'Star'"
              circle
              @click="toggleFavorite(p)"
            />
            <el-button size="small" :icon="'Edit'" circle @click="openEditor(p)" />
            <el-button size="small" type="danger" :icon="'Delete'" circle @click="deletePrompt(p)" />
          </div>
        </div>
        <p class="prompt-content">{{ p.content }}</p>
        <div class="prompt-footer">
          <el-tag size="small">{{ p.category }}</el-tag>
          <el-button size="small" text type="primary" :icon="'Upload'" @click="loadPrompt(p)">
            Load
          </el-button>
        </div>
      </div>

      <div v-if="!loading && prompts.length === 0" class="empty-state">
        <el-empty description="No prompts yet" />
      </div>
    </div>

    <el-dialog
      v-model="editorVisible"
      :title="editingId ? 'Edit Prompt' : 'New Prompt'"
      width="500px"
    >
      <el-form :model="form" label-position="top">
        <el-form-item label="Title">
          <el-input v-model="form.title" placeholder="Prompt title" />
        </el-form-item>
        <el-form-item label="Content">
          <el-input
            v-model="form.content"
            type="textarea"
            :rows="4"
            placeholder="Prompt content"
          />
        </el-form-item>
        <el-form-item label="Category">
          <el-select v-model="form.category" style="width:100%">
            <el-option label="Realistic" value="realistic" />
            <el-option label="Anime" value="anime" />
            <el-option label="Landscape" value="landscape" />
            <el-option label="Portrait" value="portrait" />
            <el-option label="Custom" value="custom" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editorVisible = false">Cancel</el-button>
        <el-button type="primary" @click="savePrompt" :loading="saving">Save</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '@/api'

const prompts = ref([])
const loading = ref(false)
const activeCategory = ref('')
const editorVisible = ref(false)
const editingId = ref(null)
const saving = ref(false)

const form = reactive({
  title: '',
  content: '',
  category: 'custom',
})

onMounted(() => fetchPrompts())

async function fetchPrompts() {
  loading.value = true
  try {
    const res = await api.get('/api/prompts', {
      params: { category: activeCategory.value || undefined },
    })
    prompts.value = res.data || []
  } catch (e) {
    ElMessage.error('Failed to fetch prompts')
  } finally {
    loading.value = false
  }
}

function openEditor(prompt) {
  if (prompt) {
    editingId.value = prompt.id
    form.title = prompt.title
    form.content = prompt.content
    form.category = prompt.category
  } else {
    editingId.value = null
    form.title = ''
    form.content = ''
    form.category = 'custom'
  }
  editorVisible.value = true
}

async function savePrompt() {
  if (!form.title.trim() || !form.content.trim()) {
    ElMessage.warning('Please fill all fields')
    return
  }

  saving.value = true
  try {
    if (editingId.value) {
      await api.put(`/api/prompts/${editingId.value}`, form)
      ElMessage.success('Updated')
    } else {
      await api.post('/api/prompts', form)
      ElMessage.success('Created')
    }
    editorVisible.value = false
    await fetchPrompts()
  } catch (e) {
    ElMessage.error('Failed to save')
  } finally {
    saving.value = false
  }
}

async function toggleFavorite(p) {
  try {
    await api.put(`/api/prompts/${p.id}`, { favorite: !p.favorite })
    p.favorite = !p.favorite
  } catch (e) {
    ElMessage.error('Failed to update')
  }
}

async function deletePrompt(p) {
  try {
    await ElMessageBox.confirm('Delete this prompt?', 'Confirm')
    await api.delete(`/api/prompts/${p.id}`)
    prompts.value = prompts.value.filter(item => item.id !== p.id)
    ElMessage.success('Deleted')
  } catch (e) {
    if (e !== 'cancel') ElMessage.error('Failed to delete')
  }
}

function loadPrompt(p) {
  ElMessage.success('Prompt loaded! Go to Text to Image page.')
}
</script>

<style scoped>
.prompts-page {
  padding: 20px;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.page-header h2 {
  font-size: 18px;
  font-weight: 600;
}

.category-tabs {
  margin-bottom: 20px;
}

.prompts-grid {
  flex: 1;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 16px;
  overflow-y: auto;
}

.prompt-card {
  background: var(--bg-secondary);
  border-radius: 8px;
  border: 1px solid var(--border-color);
  padding: 16px;
  display: flex;
  flex-direction: column;
}

.prompt-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.prompt-title {
  font-weight: 600;
  font-size: 14px;
}

.prompt-card-actions {
  display: flex;
  gap: 4px;
}

.prompt-content {
  font-size: 12px;
  color: var(--text-secondary);
  flex: 1;
  margin-bottom: 12px;
  line-height: 1.5;
}

.prompt-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.empty-state {
  grid-column: 1 / -1;
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 300px;
}
</style>
