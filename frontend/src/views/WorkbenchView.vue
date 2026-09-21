<template>
  <div class="workbench">
    <aside class="left-sidebar">
      <div class="project-head">
        <RouterLink to="/projects" class="back">← 项目列表</RouterLink>
        <h2>{{ project?.name || '加载中…' }}</h2>
        <p class="desc">{{ project?.description }}</p>
        <div class="members">
          <span v-for="member in project?.members || []" :key="member" class="member-tag">{{ member }}</span>
        </div>
      </div>

      <UploadPanel @uploaded="onUploaded" />

      <div class="imageset-list">
        <h3>采集记录</h3>
        <div
          v-for="item in imagesets"
          :key="item.id"
          class="imageset-item"
          :class="{ active: currentImageset?.id === item.id }"
          @click="openImageset(item.id)"
        >
          <strong>{{ item.title }}</strong>
          <span class="status" :class="item.status">{{ statusText(item.status) }}</span>
          <small>{{ item.created_by }}</small>
        </div>
      </div>
    </aside>

    <section class="main-area">
      <div v-if="!currentImageset" class="empty-state">
        <p>请从左侧选择一次多光谱采集，或上传新的可见光/红外/紫外图像</p>
      </div>

      <template v-else>
        <Toolbar
          :layers="currentImageset.layers"
          :band="band"
          :online-users="onlineUsers"
          @switch-band="band = $event"
        />

        <div v-if="currentImageset.status !== 'ready'" class="status-banner" :class="currentImageset.status">
          <template v-if="currentImageset.status === 'failed'">
            配准失败：{{ currentImageset.error }}
            <button class="btn tiny" @click="reprocess">重新配准</button>
          </template>
          <template v-else>SIFT 特征配准与融合处理中，请稍候…</template>
        </div>

        <MuralViewer
          v-if="currentImageset.status === 'ready'"
          ref="viewerRef"
          :layers="currentImageset.layers"
          :band="band"
          :tool="tool"
          :disease-type="diseaseType"
          @select="onSelect"
          @create="onCreate"
        />

        <div class="match-stats" v-if="currentImageset.status === 'ready' && hasStats">
          <span v-for="(stat, bandName) in currentImageset.match_stats" :key="bandName">
            {{ bandLabel(bandName) }}：匹配 {{ stat.good_matches }} / 内点 {{ stat.inliers }}
          </span>
        </div>
      </template>
    </section>

    <aside class="right-sidebar" v-if="currentImageset?.status === 'ready'">
      <AnnotationPanel
        v-model:disease-type="diseaseType"
        :tool="tool"
        :selected="selected"
        :annotations="annotations"
        @tool-change="tool = $event"
        @finish-polygon="viewerRef?.finishPolygon()"
        @cancel-draft="viewerRef?.cancelDraft()"
        @select-item="focusAnnotation"
      />
      <VersionPanel :versions="versions" :base-version="baseVersion" />
    </aside>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'

import AnnotationPanel from '@/components/AnnotationPanel.vue'
import MuralViewer from '@/components/MuralViewer.vue'
import Toolbar from '@/components/Toolbar.vue'
import UploadPanel from '@/components/UploadPanel.vue'
import VersionPanel from '@/components/VersionPanel.vue'
import { uploadApi } from '@/api'
import { projectManager } from '@/modules/project_manager/project_manager'

const route = useRoute()
const projectId = route.params.projectId

const viewerRef = ref(null)
const band = ref('fused')
const tool = ref('select')
const diseaseType = ref('flaking')
const selected = ref(null)
let pollTimer = null

const project = computed(() => projectManager.currentProject)
const imagesets = computed(() => projectManager.imagesets)
const currentImageset = computed(() => projectManager.currentImageset)
const annotations = computed(() => projectManager.annotations)
const versions = computed(() => projectManager.versions)
const baseVersion = computed(() => projectManager.baseVersion)
const onlineUsers = computed(() => projectManager.onlineUsers)
const hasStats = computed(() => Object.keys(currentImageset.value?.match_stats || {}).length > 0)

onMounted(async () => {
  await projectManager.openProject(projectId)
  const unsubscribe = projectManager.subscribe(() => {
    selected.value = selected.value
      ? projectManager.annotations.find((item) => item.id === selected.value.id) || null
      : null
  })
  projectManager.onStatusChange(() => {})
  pollTimer = setInterval(pollIfProcessing, 3000)
  onBeforeUnmount(() => {
    unsubscribe()
    clearInterval(pollTimer)
    projectManager.dispose()
  })
})

async function pollIfProcessing() {
  const item = projectManager.currentImageset
  if (item && ['uploaded', 'processing'].includes(item.status)) {
    await projectManager.refreshImageset()
  }
}

async function onUploaded(imageset) {
  await projectManager.openImageset(imageset.id)
}

async function openImageset(imagesetId) {
  selected.value = null
  tool.value = 'select'
  await projectManager.openImageset(imagesetId)
}

function onSelect(annotation) {
  selected.value = annotation
}

async function onCreate(geometry) {
  try {
    await projectManager.createAnnotation({
      disease_type: diseaseType.value,
      geometry,
      note: '',
      confidence: 1,
    })
    tool.value = 'select'
  } catch (err) {
    window.alert(err.response?.data?.detail || '标注保存失败，请刷新后重试')
  }
}

function focusAnnotation(annotation) {
  selected.value = annotation
}

async function reprocess() {
  await uploadApi.reprocess(projectId, currentImageset.value.id)
  await projectManager.refreshImageset()
}

function statusText(status) {
  return { uploaded: '待处理', processing: '配准中', ready: '已就绪', failed: '失败' }[status] || status
}

function bandLabel(key) {
  return { ir: '红外', uv: '紫外' }[key] || key
}
</script>

<style scoped>
.workbench {
  display: grid;
  grid-template-columns: 280px 1fr 320px;
  height: 100vh;
  overflow: hidden;
}
.left-sidebar, .right-sidebar {
  background: var(--panel);
  border-right: 1px solid var(--border);
  padding: 18px;
  overflow-y: auto;
}
.right-sidebar { border-right: none; border-left: 1px solid var(--border); display: flex; flex-direction: column; gap: 22px; }
.project-head h2 { margin: 8px 0; font-size: 18px; }
.back { color: var(--text-dim); text-decoration: none; font-size: 13px; }
.desc { color: var(--text-dim); font-size: 13px; }
.members { display: flex; flex-wrap: wrap; gap: 6px; }
.member-tag {
  font-size: 11px;
  padding: 2px 8px;
  background: var(--panel-light);
  border-radius: 10px;
}
.imageset-list { margin-top: 24px; }
.imageset-list h3 { font-size: 14px; color: var(--text-dim); }
.imageset-item {
  display: flex;
  flex-direction: column;
  gap: 3px;
  padding: 10px;
  border: 1px solid var(--border);
  border-radius: 8px;
  margin-bottom: 8px;
  cursor: pointer;
}
.imageset-item.active, .imageset-item:hover { border-color: var(--accent); }
.imageset-item small { color: var(--text-dim); }
.status { font-size: 12px; }
.status.ready { color: #3aa55a; }
.status.processing, .status.uploaded { color: var(--accent); }
.status.failed { color: var(--danger); }
.main-area { position: relative; background: #100f0d; }
.empty-state {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  color: var(--text-dim);
  padding: 40px;
  text-align: center;
}
.viewer-toolbar {
  position: absolute;
  top: 12px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 30;
  display: flex;
  gap: 16px;
  align-items: center;
  background: rgba(42, 38, 34, 0.92);
  padding: 6px 10px;
  border-radius: 8px;
  border: 1px solid var(--border);
}
.band-switch { display: flex; gap: 6px; }
.btn.tiny { padding: 4px 10px; font-size: 12px; }
.online { display: flex; gap: 8px; font-size: 12px; color: #9fd0ff; }
.status-banner {
  position: absolute;
  top: 70px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 30;
  padding: 10px 18px;
  border-radius: 8px;
  background: rgba(200, 137, 63, 0.95);
  color: #1d1b18;
  font-size: 13px;
}
.status-banner.failed { background: rgba(232, 80, 74, 0.95); color: #fff; }
.match-stats {
  position: absolute;
  bottom: 12px;
  left: 12px;
  z-index: 30;
  display: flex;
  gap: 14px;
  background: rgba(29, 27, 24, 0.85);
  padding: 6px 12px;
  border-radius: 6px;
  font-size: 12px;
  color: var(--text-dim);
}
</style>
