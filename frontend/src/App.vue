<template>
  <div class="app-container" :class="{ 'sidebar-collapsed': appStore.sidebarCollapsed }">
    <aside class="sidebar">
      <div class="sidebar-header">
        <div class="logo">
          <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
            <rect width="28" height="28" rx="6" fill="#6366f1"/>
            <path d="M8 20L14 8L20 20H8Z" fill="white" opacity="0.9"/>
            <circle cx="14" cy="14" r="3" fill="white"/>
          </svg>
          <span class="logo-text" v-show="!appStore.sidebarCollapsed">MFlux Studio</span>
        </div>
        <el-button
          :icon="Fold"
          text
          class="collapse-btn"
          @click="appStore.sidebarCollapsed = !appStore.sidebarCollapsed"
        />
      </div>

      <el-menu
        :default-active="route.path"
        :collapse="appStore.sidebarCollapsed"
        router
        class="sidebar-menu"
      >
        <el-menu-item index="/text2img">
          <el-icon><EditPen /></el-icon>
          <template #title>Text to Image</template>
        </el-menu-item>
        <el-menu-item index="/img2img">
          <el-icon><Picture /></el-icon>
          <template #title>Image to Image</template>
        </el-menu-item>
        <el-menu-item index="/history">
          <el-icon><Clock /></el-icon>
          <template #title>History</template>
        </el-menu-item>
        <el-menu-item index="/prompts">
          <el-icon><Collection /></el-icon>
          <template #title>Prompts</template>
        </el-menu-item>
        <el-menu-item index="/models">
          <el-icon><Monitor /></el-icon>
          <template #title>Models</template>
        </el-menu-item>
        <el-menu-item index="/browser">
          <el-icon><Grid /></el-icon>
          <template #title>Browser</template>
        </el-menu-item>
        <el-menu-item index="/settings">
          <el-icon><Setting /></el-icon>
          <template #title>Settings</template>
        </el-menu-item>
      </el-menu>

      <div class="sidebar-footer">
        <el-button
          :icon="appStore.darkMode ? 'Sunny' : 'Moon'"
          text
          @click="appStore.toggleDark()"
        >
          <template #title>{{ appStore.darkMode ? 'Light' : 'Dark' }}</template>
        </el-button>
        <el-tag :type="appStore.wsConnected ? 'success' : 'danger'" size="small" effect="plain">
          {{ appStore.wsConnected ? '●' : '○' }}
        </el-tag>
      </div>
    </aside>

    <main class="main-content">
      <router-view />
    </main>

    <TaskPanel />
  </div>
</template>

<script setup>
import { onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { Fold } from '@element-plus/icons-vue'
import { useAppStore } from '@/stores/app'
import TaskPanel from '@/components/TaskPanel.vue'

const appStore = useAppStore()
const route = useRoute()

onMounted(() => {
  appStore.applyTheme()
  appStore.connectWebSocket()
})

onUnmounted(() => {
  appStore.disconnectWebSocket()
})
</script>

<style scoped>
.app-container {
  display: flex;
  height: 100vh;
  overflow: hidden;
}

.sidebar {
  width: var(--sidebar-width);
  background: var(--bg-sidebar);
  display: flex;
  flex-direction: column;
  transition: width 0.3s;
  flex-shrink: 0;
  overflow: hidden;
}

.sidebar-collapsed .sidebar {
  width: 64px;
}

.sidebar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid rgba(255,255,255,0.1);
}

.logo {
  display: flex;
  align-items: center;
  gap: 10px;
}

.logo-text {
  color: #fff;
  font-size: 15px;
  font-weight: 600;
  white-space: nowrap;
}

.collapse-btn {
  color: rgba(255,255,255,0.6);
}

.sidebar-menu {
  flex: 1;
  border-right: none;
  background: transparent;
}

.sidebar-menu .el-menu-item {
  color: rgba(255,255,255,0.7);
}

.sidebar-menu .el-menu-item.is-active {
  color: #fff;
  background: rgba(99,102,241,0.2);
}

.sidebar-menu .el-menu-item:hover {
  background: rgba(255,255,255,0.05);
}

.sidebar-footer {
  padding: 12px 16px;
  border-top: 1px solid rgba(255,255,255,0.1);
  display: flex;
  align-items: center;
  gap: 8px;
  color: rgba(255,255,255,0.6);
}

.main-content {
  flex: 1;
  overflow-y: auto;
  background: var(--bg-primary);
}
</style>
