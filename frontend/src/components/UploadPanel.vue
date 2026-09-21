<template>
  <div class="panel">
    <h3>新建多光谱采集</h3>
    <div class="field">
      <label>标题（洞窟/区域）</label>
      <input v-model="title" placeholder="如：257 窟西壁-九色鹿局部" />
    </div>
    <div v-for="band in bandInputs" :key="band.key" class="field">
      <label>{{ band.label }}<span v-if="band.required" class="required">*</span></label>
      <input type="file" accept="image/*,.tif,.tiff" @change="onFile(band.key, $event)" />
    </div>
    <div v-if="progress > 0 && progress < 1" class="progress">
      <div :style="{ width: `${progress * 100}%` }" />
    </div>
    <p v-if="error" class="error">{{ error }}</p>
    <button class="btn primary" style="width: 100%" :disabled="!canSubmit" @click="submit">
      上传并配准
    </button>
  </div>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'

import { projectManager } from '@/modules/project_manager/project_manager'

const emit = defineEmits(['uploaded'])
const title = ref('')
const progress = ref(0)
const error = ref('')
const files = reactive({ visible: null, ir: null, uv: null })

const bandInputs = [
  { key: 'visible', label: '可见光（配准基准）', required: true },
  { key: 'ir', label: '红外', required: false },
  { key: 'uv', label: '紫外', required: false },
]

const canSubmit = computed(() => Boolean(title.value && files.visible))

function onFile(key, event) {
  files[key] = event.target.files[0] || null
}

async function submit() {
  error.value = ''
  try {
    const imageset = await projectManager.uploadImageset(files, title.value, (ratio) => {
      progress.value = ratio
    })
    title.value = ''
    Object.assign(files, { visible: null, ir: null, uv: null })
    progress.value = 0
    emit('uploaded', imageset)
  } catch (err) {
    error.value = err.response?.data?.detail || '上传失败'
  }
}
</script>

<style scoped>
.panel h3 { margin: 0 0 14px; color: var(--accent); }
.required { color: var(--danger); margin-left: 4px; }
.progress {
  height: 6px;
  background: #1f1c19;
  border-radius: 3px;
  overflow: hidden;
  margin-bottom: 12px;
}
.progress div { height: 100%; background: var(--accent); transition: width 0.2s; }
.error { color: var(--danger); font-size: 13px; }
</style>
