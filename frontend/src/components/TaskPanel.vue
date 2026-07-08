<template>
  <div class="task-panel" v-if="appStore.tasks.length > 0">
    <div class="task-panel-header">
      <span class="task-panel-title">Tasks</span>
      <div class="task-panel-actions">
        <el-button size="small" text @click="appStore.clearQueue()">Clear</el-button>
        <el-button size="small" text @click="showPanel = !showPanel">
          {{ showPanel ? 'Hide' : 'Show' }}
        </el-button>
      </div>
    </div>
    <div class="task-list" v-show="showPanel">
      <div
        v-for="task in appStore.tasks"
        :key="task.task_id"
        class="task-item"
      >
        <div class="task-info">
          <el-tag :type="statusType(task.status)" size="small" effect="plain">
            {{ task.status }}
          </el-tag>
          <span class="task-prompt">{{ truncate(task.prompt, 30) }}</span>
        </div>
        <div class="task-meta" v-if="task.queued_at">
          <span class="task-time">Start {{ formatTime(task.queued_at) }}</span>
          <span class="task-duration" v-if="task.elapsed">{{ formatDuration(task.elapsed) }}</span>
        </div>
        <div class="task-progress" v-if="task.status === 'running'">
          <el-progress
            :percentage="task.progress"
            :stroke-width="4"
            :show-text="true"
            :format="() => task.current_step + '/' + task.total_steps"
          />
        </div>
        <div class="task-actions" v-if="task.status === 'waiting' || task.status === 'running'">
          <el-button
            size="small"
            text
            type="danger"
            @click="appStore.cancelTask(task.task_id)"
          >
            Cancel
          </el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useAppStore } from '@/stores/app'

const appStore = useAppStore()
const showPanel = ref(true)

function statusType(status) {
  const map = { waiting: 'info', running: 'warning', completed: 'success', failed: 'danger', cancelled: 'info' }
  return map[status] || 'info'
}

function truncate(str, len) {
  return str?.length > len ? str.slice(0, len) + '...' : str
}

function formatTime(timestamp) {
  if (!timestamp) return ''
  const d = new Date(timestamp * 1000)
  return d.toLocaleTimeString()
}

function formatDuration(seconds) {
  if (!seconds && seconds !== 0) return ''
  if (seconds < 60) return seconds.toFixed(1) + 's'
  const m = Math.floor(seconds / 60)
  const s = Math.floor(seconds % 60)
  return m + 'm ' + s + 's'
}

onMounted(() => {
  appStore.fetchTasks()
})
</script>

<style scoped>
.task-panel {
  position: fixed;
  bottom: 0;
  right: 20px;
  width: 360px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 8px 8px 0 0;
  box-shadow: 0 -2px 12px rgba(0,0,0,0.1);
  z-index: 9999;
  max-height: 300px;
  overflow: hidden;
}

.task-panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  border-bottom: 1px solid var(--border-color);
}

.task-panel-title {
  font-weight: 600;
  font-size: 13px;
}

.task-list {
  max-height: 250px;
  overflow-y: auto;
  padding: 4px 0;
}

.task-item {
  padding: 8px 12px;
  border-bottom: 1px solid var(--border-color);
}

.task-info {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.task-prompt {
  font-size: 12px;
  color: var(--text-secondary);
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.task-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
  font-size: 11px;
  color: var(--text-secondary);
}

.task-progress {
  display: flex;
  align-items: center;
  gap: 8px;
}

.task-progress .el-progress {
  flex: 1;
}

.task-actions {
  text-align: right;
}
</style>
