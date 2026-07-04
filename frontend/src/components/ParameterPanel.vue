<template>
  <div class="param-panel">
    <el-form :model="params" label-position="top" size="small">
      <div class="param-row">
        <el-form-item label="Width">
          <el-select v-model="params.width" style="width:100%">
            <el-option label="512" :value="512" />
            <el-option label="768" :value="768" />
            <el-option label="1024" :value="1024" />
            <el-option label="1280" :value="1280" />
            <el-option label="1536" :value="1536" />
          </el-select>
        </el-form-item>
        <el-form-item label="Height">
          <el-select v-model="params.height" style="width:100%">
            <el-option label="512" :value="512" />
            <el-option label="768" :value="768" />
            <el-option label="1024" :value="1024" />
            <el-option label="1280" :value="1280" />
            <el-option label="1536" :value="1536" />
          </el-select>
        </el-form-item>
      </div>

      <el-form-item label="Steps">
        <el-slider
          v-model="params.steps"
          :min="1"
          :max="50"
          :step="1"
          show-input
          :input-size="'small'"
        />
      </el-form-item>

      <el-form-item label="Guidance Scale (CFG)">
        <el-slider
          v-model="params.guidance"
          :min="1"
          :max="20"
          :step="0.5"
          show-input
          :input-size="'small'"
        />
      </el-form-item>

      <el-form-item label="Seed">
        <div class="seed-row">
          <el-input v-model.number="params.seed" :placeholder="randomSeed ? 'Random' : 'Enter seed'" />
          <el-button :icon="Refresh" @click="randomizeSeed" />
        </div>
      </el-form-item>

      <el-form-item label="Batch Count" v-if="showBatch">
        <el-input-number v-model="params.batch_count" :min="1" :max="8" />
      </el-form-item>

      <el-form-item label="Model">
        <el-select v-model="params.model" style="width:100%" placeholder="Default model">
          <el-option label="Default" value="" />
          <el-option
            v-for="m in models"
            :key="m.id"
            :label="m.name"
            :value="m.path"
          />
        </el-select>
      </el-form-item>
    </el-form>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { Refresh } from '@element-plus/icons-vue'

const props = defineProps({
  params: { type: Object, required: true },
  models: { type: Array, default: () => [] },
  showBatch: { type: Boolean, default: true },
})

const emit = defineEmits(['update:params'])
const randomSeed = ref(!props.params.seed)

function randomizeSeed() {
  props.params.seed = Math.floor(Math.random() * 2147483647)
  randomSeed.value = false
}
</script>

<style scoped>
.param-panel {
  padding: 0;
}

.param-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.seed-row {
  display: flex;
  gap: 8px;
}

.seed-row .el-input {
  flex: 1;
}

.el-form-item {
  margin-bottom: 16px;
}
</style>
