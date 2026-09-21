<template>
  <div class="panel">
    <h3>标注版本</h3>
    <div class="commit-row">
      <input v-model="comment" placeholder="版本备注，如：西壁复核完成" @keyup.enter="commit" />
      <button class="btn primary" @click="commit">提交版本</button>
    </div>
    <p class="base">当前基准版本：v{{ baseVersion ?? 0 }}</p>
    <p v-if="error" class="error">{{ error }}</p>

    <ul class="versions">
      <li v-for="version in versions" :key="version.version">
        <div class="ver-head">
          <strong>v{{ version.version }}</strong>
          <span>{{ version.annotation_count }} 处标注</span>
        </div>
        <p>{{ version.comment }}</p>
        <footer>
          <span>{{ version.created_by }} · {{ formatTime(version.created_at) }}</span>
          <button
            class="btn tiny"
            :disabled="version.version === baseVersion"
            @click="rollbackTo(version.version)"
          >
            回滚
          </button>
        </footer>
      </li>
    </ul>
  </div>
</template>

<script setup>
import { ref } from 'vue'

import { projectManager } from '@/modules/project_manager/project_manager'

defineProps({
  versions: { type: Array, default: () => [] },
  baseVersion: Number,
})

const comment = ref('')
const error = ref('')

async function commit() {
  error.value = ''
  try {
    await projectManager.commitVersion(comment.value)
    comment.value = ''
  } catch (err) {
    error.value = err.response?.data?.detail || '提交失败'
  }
}

async function rollbackTo(version) {
  if (!window.confirm(`确认将标注回滚到 v${version}？将生成一个新版本，不会丢失历史。`)) return
  error.value = ''
  try {
    await projectManager.rollback(version, `回滚至 v${version}`)
  } catch (err) {
    error.value = err.response?.data?.detail || '回滚失败'
  }
}

function formatTime(value) {
  return new Date(value).toLocaleString('zh-CN', { hour12: false })
}
</script>

<style scoped>
h3 { margin: 0 0 14px; color: var(--accent); }
.commit-row { display: flex; gap: 6px; }
.commit-row input { flex: 1; }
.base { font-size: 12px; color: var(--text-dim); }
.error { color: var(--danger); font-size: 13px; }
.versions {
  list-style: none;
  margin: 12px 0 0;
  padding: 0;
  max-height: 320px;
  overflow-y: auto;
}
.versions li {
  padding: 10px;
  border: 1px solid var(--border);
  border-radius: 8px;
  margin-bottom: 8px;
}
.ver-head { display: flex; justify-content: space-between; font-size: 13px; }
.ver-head span { color: var(--text-dim); }
.versions p { font-size: 12px; color: var(--text-dim); margin: 6px 0; }
.versions footer { display: flex; justify-content: space-between; align-items: center; font-size: 11px; color: var(--text-dim); }
.btn.tiny { padding: 3px 10px; font-size: 12px; }
</style>
