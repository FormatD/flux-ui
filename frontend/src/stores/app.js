import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import api from '@/api'

export const useAppStore = defineStore('app', () => {
  const darkMode = ref(false)
  const sidebarCollapsed = ref(false)
  const currentTaskId = ref('')
  const tasks = ref([])
  const wsConnected = ref(false)

  let ws = null
  let reconnectTimer = null

  function toggleDark() {
    darkMode.value = !darkMode.value
    applyTheme()
  }

  function applyTheme() {
    if (darkMode.value) {
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.classList.remove('dark')
    }
  }

  function connectWebSocket() {
    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${protocol}//${location.host}/ws`

    try {
      ws = new WebSocket(wsUrl)

      ws.onopen = () => {
        wsConnected.value = true
        ws.send(JSON.stringify({ type: 'subscribe' }))
      }

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          handleMessage(data)
        } catch (e) {
          console.error('WS parse error:', e)
        }
      }

      ws.onclose = () => {
        wsConnected.value = false
        scheduleReconnect()
      }

      ws.onerror = () => {
        wsConnected.value = false
      }
    } catch (e) {
      scheduleReconnect()
    }
  }

  function scheduleReconnect() {
    if (reconnectTimer) clearTimeout(reconnectTimer)
    reconnectTimer = setTimeout(() => connectWebSocket(), 3000)
  }

  function handleMessage(data) {
    if (data.type === 'progress') {
      updateTaskProgress(data)
    } else if (data.type === 'task_error') {
      ElMessage.error(`Task failed: ${data.error}`)
      fetchTasks()
    } else if (data.type === 'task_completed') {
      fetchTasks()
    }
  }

  function updateTaskProgress(data) {
    const idx = tasks.value.findIndex(t => t.task_id === data.task_id)
    if (idx >= 0) {
      tasks.value[idx].progress = data.percent || 0
      tasks.value[idx].current_step = data.current_step || 0
      tasks.value[idx].total_steps = data.total_steps || 0
      tasks.value[idx].elapsed = data.elapsed || 0
    }
  }

  async function fetchTasks() {
    try {
      const res = await api.get('/api/tasks/queue')
      tasks.value = res.data || []
    } catch (e) {
      console.error('Failed to fetch tasks')
    }
  }

  async function cancelTask(taskId) {
    try {
      await api.post(`/api/tasks/${taskId}/cancel`)
      ElMessage.success('Task cancelled')
      await fetchTasks()
    } catch (e) {
      ElMessage.error('Failed to cancel task')
    }
  }

  async function clearQueue() {
    try {
      await api.post('/api/tasks/cancel-all')
      ElMessage.success('Queue cleared')
      await fetchTasks()
    } catch (e) {
      ElMessage.error('Failed to clear queue')
    }
  }

  function disconnectWebSocket() {
    if (reconnectTimer) {
      clearTimeout(reconnectTimer)
      reconnectTimer = null
    }
    if (ws) {
      ws.close()
      ws = null
    }
  }

  return {
    darkMode,
    sidebarCollapsed,
    currentTaskId,
    tasks,
    wsConnected,
    toggleDark,
    applyTheme,
    connectWebSocket,
    disconnectWebSocket,
    fetchTasks,
    cancelTask,
    clearQueue,
  }
}, {
  persist: {
    key: 'mflux-studio',
    paths: ['darkMode', 'sidebarCollapsed'],
  },
})
