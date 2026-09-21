<template>
  <div class="panel annotation-panel">
    <h3>病害标注</h3>
    <div class="disease-group">
      <button
        v-for="disease in DISEASE_TYPES"
        :key="disease.value"
        class="btn disease-btn"
        :class="{ active: diseaseType === disease.value }"
        @click="$emit('update:diseaseType', disease.value)"
      >
        <span class="dot" :style="{ background: disease.color }" />
        {{ disease.label }}
      </button>
    </div>

    <div class="tool-group">
      <button class="btn" :class="{ active: tool === 'select' }" @click="setTool('select')">选择</button>
      <button class="btn" :class="{ active: tool === 'polygon' }" @click="setTool('polygon')">多边形</button>
      <button class="btn" :class="{ active: tool === 'rectangle' }" @click="setTool('rectangle')">矩形</button>
    </div>

    <p v-if="tool === 'polygon'" class="hint">
      单击添加顶点，双击起点完成；
      <a @click="$emit('finish-polygon')">立即完成</a> ·
      <a @click="$emit('cancel-draft')">取消</a>
    </p>

    <div v-if="selected" class="editor">
      <h4>选中区域</h4>
      <label>类型</label>
      <select :value="selected.disease_type" @change="changeType($event.target.value)">
        <option v-for="disease in DISEASE_TYPES" :key="disease.value" :value="disease.value">
          {{ disease.label }}
        </option>
      </select>
      <label>备注</label>
      <textarea :value="selected.note" rows="2" @change="changeNote($event.target.value)" />
      <p class="meta">
        {{ diseaseLabel(selected.disease_type) }} · {{ selected.created_by }} 标注
      </p>
      <button class="btn danger" @click="remove">删除该区域</button>
    </div>

    <div class="list">
      <h4>标注列表（{{ annotations.length }}）</h4>
      <div
        v-for="annotation in annotations"
        :key="annotation.id"
        class="list-item"
        @click="$emit('select-item', annotation)"
      >
        <span class="dot" :style="{ background: diseaseColor(annotation.disease_type) }" />
        <span>{{ diseaseLabel(annotation.disease_type) }}</span>
        <span class="by">{{ annotation.updated_by }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { DISEASE_TYPES, diseaseColor, diseaseLabel } from '@/constants'
import { projectManager } from '@/modules/project_manager/project_manager'

const props = defineProps({
  tool: String,
  diseaseType: String,
  selected: Object,
  annotations: { type: Array, default: () => [] },
})
const emit = defineEmits(['update:diseaseType', 'tool-change', 'finish-polygon', 'cancel-draft', 'select-item'])

function setTool(tool) {
  emit('tool-change', tool)
}

async function changeType(disease_type) {
  await projectManager.updateAnnotation(props.selected.id, { disease_type })
}

async function changeNote(note) {
  await projectManager.updateAnnotation(props.selected.id, { note })
}

async function remove() {
  await projectManager.deleteAnnotation(props.selected.id)
}
</script>

<style scoped>
.annotation-panel h3 { margin: 0 0 14px; color: var(--accent); }
.disease-group, .tool-group {
  display: flex;
  gap: 6px;
  margin-bottom: 10px;
}
.disease-group .btn, .tool-group .btn { flex: 1; padding: 8px 4px; font-size: 13px; }
.dot {
  display: inline-block;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  margin-right: 6px;
}
.hint { font-size: 12px; color: var(--text-dim); }
.hint a { color: var(--accent); cursor: pointer; margin: 0 2px; }
.editor {
  border-top: 1px solid var(--border);
  padding-top: 12px;
  margin-top: 12px;
}
.editor label { display: block; font-size: 12px; color: var(--text-dim); margin: 8px 0 4px; }
.meta { font-size: 12px; color: var(--text-dim); }
.list { margin-top: 16px; }
.list h4 { margin: 0 0 8px; font-size: 13px; color: var(--text-dim); }
.list-item {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 7px 8px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
}
.list-item:hover { background: var(--panel-light); }
.list-item .by { margin-left: auto; color: var(--text-dim); font-size: 12px; }
</style>
