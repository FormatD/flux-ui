import { defineStore } from 'pinia'
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import api from '@/api'

export const useAppStore = defineStore('app', () => {
  const darkMode = ref(false)
  const sidebarCollapsed = ref(false)
  const currentTaskId = ref('')
  const tasks = ref([])
  const wsConnected = ref(false)
  const scanProgress = ref(null)  // { task_id, message, percent, current_step, total_steps, elapsed }

  let ws = null
  let reconnectTimer = null
  let pingInterval = null
  let fallbackTimer = null

  function startFallbackPolling() {
    if (fallbackTimer) return
    fallbackTimer = setInterval(() => {
      fetchTasks()
    }, 30000)
  }

  function stopFallbackPolling() {
    if (fallbackTimer) {
      clearInterval(fallbackTimer)
      fallbackTimer = null
    }
  }

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
    // Prevent duplicate connections
    if (ws && (ws.readyState === WebSocket.CONNECTING || ws.readyState === WebSocket.OPEN)) {
      return
    }

    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${protocol}//${location.host}/ws`

    try {
      ws = new WebSocket(wsUrl)

      ws.onopen = () => {
        wsConnected.value = true
        ws.send(JSON.stringify({ type: 'subscribe' }))
        startHeartbeat()
      }

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          // Respond to server heartbeat
          if (data.type === 'ping') {
            ws.send(JSON.stringify({ type: 'pong' }))
            return
          }
          handleMessage(data)
        } catch (e) {
          console.error('WS parse error:', e)
        }
      }

     ws.onclose = () => {
       wsConnected.value = false
        stopHeartbeat()
       scheduleReconnect()
     }

      ws.onerror = () => {
        wsConnected.value = false
      }
    } catch (e) {
      scheduleReconnect()
    }
  }

  function startHeartbeat() {
    stopHeartbeat()
    pingInterval = setInterval(() => {
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'ping' }))
      }
    }, 25000)
  }

  function stopHeartbeat() {
    if (pingInterval) {
      clearInterval(pingInterval)
      pingInterval = null
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
    } else if (data.type === 'scan_progress') {
      handleScanProgress(data)
    }
  }

  function handleScanProgress(data) {
    scanProgress.value = {
      task_id: data.task_id,
      phase_or_model: data.phase_or_model,
      message: data.message,
      percent: data.percent || 0,
      current_step: data.current_step || 0,
      total_steps: data.total_steps || 0,
      elapsed: data.elapsed || 0,
    }
    // Clear scan progress on completion or error
    if (data.phase_or_model === '_done' || data.phase_or_model === '_error') {
      if (data.phase_or_model === '_error') {
        ElMessage.error(data.message || 'Scan failed')
      }
      // Keep the final state for 3s so the UI can show completion, then clear
      setTimeout(() => {
        scanProgress.value = null
      }, 3000)
    }
  }

  function clearScanProgress() {
    scanProgress.value = null
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
      tasks.value = []
      ElMessage.success('Queue cleared')
    } catch (e) {
      ElMessage.error('Failed to clear queue')
    }
  }

  function disconnectWebSocket() {
    stopHeartbeat()
    stopFallbackPolling()
    if (reconnectTimer) {
      clearTimeout(reconnectTimer)
      reconnectTimer = null
    }
    if (ws) {
      ws.close()
      ws = null
    }
  }

  // Start 30s fallback polling as safety net (WebSocket is primary)
  startFallbackPolling()

  return {
    darkMode,
    sidebarCollapsed,
    currentTaskId,
    tasks,
    wsConnected,
    scanProgress,
    toggleDark,
    applyTheme,
    connectWebSocket,
    disconnectWebSocket,
    fetchTasks,
    cancelTask,
    clearQueue,
    clearScanProgress,
    startFallbackPolling,
    stopFallbackPolling,
  }
}, {
  persist: {
    key: 'mflux-studio',
    paths: ['darkMode', 'sidebarCollapsed'],
  },
})
