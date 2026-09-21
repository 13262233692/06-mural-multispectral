<template>
  <div class="layout">
    <header>
      <h1>敦煌壁画多光谱图像处理平台</h1>
      <div class="user">
        <input
          v-model="userInput"
          placeholder="输入用户名以协作"
          @change="pm.setUser(userInput)"
        />
        <span v-if="pm.state.status" class="status">{{ pm.state.status }}</span>
      </div>
    </header>

    <aside>
      <section>
        <h2>项目</h2>
        <div class="row">
          <input v-model="newProject" placeholder="新项目名称" />
          <button :disabled="!pm.state.user" @click="createProject">创建</button>
        </div>
        <ul>
          <li
            v-for="p in pm.state.projects"
            :key="p.project_id"
            :class="{ active: pm.state.project?.project_id === p.project_id }"
            @click="pm.selectProject(p)"
          >
            {{ p.name }}
          </li>
        </ul>
      </section>

      <section v-if="pm.state.project">
        <h2>波段上传</h2>
        <div v-for="b in bands" :key="b.key" class="row">
          <label>{{ b.zh }}</label>
          <input type="file" accept="image/*" @change="upload(b.key, $event)" />
        </div>
        <button :disabled="!pm.state.imageSet" @click="pm.register()">
          SIFT 配准 + 融合
        </button>
        <div v-if="pm.state.imageSet?.registered" class="stats">
          <div v-for="(s, band) in pm.state.imageSet.registered.stats" :key="band">
            {{ band }}: {{ s.inliers }}/{{ s.matches }} 内点
          </div>
        </div>
      </section>

      <section v-if="pm.state.imageSet?.registered">
        <h2>标注工具</h2>
        <div class="row">
          <button :class="{ on: mode === 'pan' }" @click="setMode('pan')">浏览</button>
          <button :class="{ on: mode === 'draw' }" @click="setMode('draw')">圈选</button>
        </div>
        <div class="row labels">
          <button
            v-for="(meta, key) in LABELS"
            :key="key"
            :style="{ borderColor: meta.color }"
            :class="{ on: activeLabel === key }"
            @click="setLabel(key)"
          >
            {{ meta.zh }}
          </button>
        </div>
        <div class="row">
          <button @click="layer?.deleteSelected(); pm.markDirty()">删除选中</button>
          <button :disabled="!pm.state.dirty" @click="pm.save()">
            保存（v{{ pm.state.version + 1 }}）
          </button>
        </div>
      </section>

      <section v-if="pm.state.imageSet">
        <h2>版本历史</h2>
        <button class="link" @click="pm.loadVersions()">刷新</button>
        <ul>
          <li v-for="v in pm.state.versions" :key="v.version">
            <span>
              v{{ v.version }} · {{ v.author }} · {{ v.kind === 'rollback' ? '回滚' : '编辑' }}
              <em v-if="v.message">「{{ v.message }}」</em>
            </span>
            <button
              v-if="v.version !== pm.state.version"
              @click="pm.rollback(v.version)"
            >
              回滚
            </button>
          </li>
        </ul>
      </section>
    </aside>

    <main>
      <div id="osd-container" ref="osdRef"></div>
      <p v-if="!pm.state.imageSet?.registered" class="hint">
        上传三波段图像并执行配准后，在此查看融合结果并标注病害区域
      </p>
    </main>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { api } from './api/client'
import { ViewerCore } from './viewer/viewer_core'
import { AnnotationLayer, LABELS } from './viewer/annotation_layer'
import { ProjectManager } from './project/project_manager'

const pm = new ProjectManager()
const osdRef = ref(null)
const userInput = ref(pm.state.user)
const newProject = ref('')
const mode = ref('pan')
const activeLabel = ref('flaking')
const bands = [
  { key: 'visible', zh: '可见光' },
  { key: 'infrared', zh: '红外' },
  { key: 'ultraviolet', zh: '紫外' },
]

let core = null
let layer = null

onMounted(async () => {
  core = new ViewerCore('osd-container')
  layer = new AnnotationLayer(osdRef.value, core)
  layer.onChange = () => pm.markDirty()
  await pm.loadProjects()
  if (pm.state.imageSet?.registered) {
    core.openImage(pm.fusedImageUrl())
  }
})

async function createProject() {
  if (!newProject.value) return
  await pm.createProject(newProject.value, '')
  newProject.value = ''
}

async function upload(band, event) {
  const file = event.target.files?.[0]
  if (file) await pm.uploadBand(band, file)
}

function setMode(m) {
  mode.value = m
  layer?.setMode(m)
}

function setLabel(label) {
  activeLabel.value = label
  layer?.setLabel(label)
}

// 标注数据变化时同步到标注层
pm.state && watchAnnotations()
function watchAnnotations() {
  // 简单轮询式同步：ProjectManager 更新 state.annotations 后刷新图层
  let last = null
  setInterval(() => {
    if (!layer) return
    const url = pm.fusedImageUrl()
    if (url && core && !core.viewer.world.getItemAt(0)) core.openImage(url)
    if (pm.state.annotations !== last) {
      last = pm.state.annotations
      layer.setAnnotations(pm.state.annotations)
    }
  }, 500)
}
</script>

<style>
body { margin: 0; font-family: 'PingFang SC', sans-serif; }
.layout { display: grid; grid-template-columns: 300px 1fr; grid-template-rows: 56px 1fr; height: 100vh; }
header { grid-column: 1 / 3; display: flex; align-items: center; justify-content: space-between; padding: 0 16px; background: #2b2118; color: #f0e6d2; }
header h1 { font-size: 17px; margin: 0; }
aside { overflow-y: auto; padding: 12px; border-right: 1px solid #ddd; background: #faf7f0; }
aside section { margin-bottom: 20px; }
aside h2 { font-size: 14px; color: #7a5c2e; margin: 0 0 8px; }
main { position: relative; }
#osd-container { position: absolute; inset: 0; background: #111; }
.row { display: flex; gap: 6px; margin-bottom: 8px; align-items: center; }
button { cursor: pointer; border: 1px solid #b49b6a; background: #fff; border-radius: 4px; padding: 4px 10px; }
button.on { background: #7a5c2e; color: #fff; }
button.link { border: none; color: #7a5c2e; text-decoration: underline; }
ul { list-style: none; padding: 0; margin: 0; }
li { padding: 4px 6px; border-radius: 4px; display: flex; justify-content: space-between; align-items: center; }
li.active { background: #eadfc8; }
li:hover { background: #f1e8d5; cursor: pointer; }
.status { font-size: 12px; color: #ffd98a; margin-left: 12px; }
.hint { position: absolute; top: 40%; width: 100%; text-align: center; color: #888; }
.stats { font-size: 12px; color: #666; margin-top: 6px; }
.labels button { border-width: 2px; }
input { padding: 4px 6px; border: 1px solid #ccc; border-radius: 4px; }
</style>
