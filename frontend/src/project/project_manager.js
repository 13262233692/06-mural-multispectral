/**
 * project_manager — 项目/图像组/标注的协作状态管理。
 * 负责：加载远端标注、本地变更缓冲、乐观锁保存（409 自动合并重试）、
 * 版本历史与回滚、多用户轮询同步。
 */
import { reactive } from 'vue'
import { api } from '../api/client'

const POLL_INTERVAL_MS = 5000

export class ProjectManager {
  constructor() {
    this.state = reactive({
      user: localStorage.getItem('mural_user') || '',
      projects: [],
      project: null,
      imageSet: null,
      annotations: [],
      version: 0,
      versions: [],
      dirty: false,
      status: '',
    })
    this._serverAnnotations = []
    this._pollTimer = null
  }

  setUser(name) {
    this.state.user = name
    localStorage.setItem('mural_user', name)
  }

  async loadProjects() {
    this.state.projects = await api.listProjects()
  }

  async createProject(name, description) {
    await api.createProject({ name, description, owner: this.state.user })
    await this.loadProjects()
  }

  async selectProject(project) {
    this.state.project = project
    const sets = await api.listSets(project.project_id)
    this.state.imageSet = sets[0] || null
    if (this.state.imageSet) await this.loadAnnotations()
    this._startPolling()
  }

  async uploadBand(band, file) {
    this.state.status = `上传 ${band} 图像中…`
    const res = await api.uploadBand(this.state.project.project_id, band, file)
    const sets = await api.listSets(this.state.project.project_id)
    this.state.imageSet = sets.find((s) => s.image_set_id === res.image_set_id)
    this.state.status = '上传完成'
  }

  async register() {
    this.state.status = 'SIFT 配准与融合中…'
    await api.register(this.state.imageSet.image_set_id)
    const sets = await api.listSets(this.state.project.project_id)
    this.state.imageSet = sets.find(
      (s) => s.image_set_id === this.state.imageSet.image_set_id
    )
    this.state.status = '配准完成'
  }

  fusedImageUrl() {
    const set = this.state.imageSet
    if (!set?.registered?.fused_image) return null
    return `/results/${set.image_set_id}/${set.registered.fused_image}`
  }

  async loadAnnotations() {
    const data = await api.getAnnotations(this.state.imageSet.image_set_id)
    this._serverAnnotations = data.annotations
    this.state.annotations = [...data.annotations]
    this.state.version = data.version
    this.state.dirty = false
  }

  markDirty() {
    this.state.dirty = true
  }

  /** 保存：本地标注与服务端做 diff，乐观锁冲突时刷新后提示用户重试。 */
  async save(message = '') {
    const imageSetId = this.state.imageSet.image_set_id
    const serverIds = new Map(this._serverAnnotations.map((a) => [a.annotation_id, a]))
    const localIds = new Map(this.state.annotations.map((a) => [a.annotation_id, a]))

    const upserts = []
    const update_ids = {}
    const delete_ids = []

    for (const ann of this.state.annotations) {
      const payload = { label: ann.label, geometry: ann.geometry, note: ann.note || '' }
      if (ann._local || !serverIds.has(ann.annotation_id)) {
        upserts.push(payload)
      } else if (JSON.stringify(serverIds.get(ann.annotation_id)) !== JSON.stringify(ann)) {
        update_ids[ann.annotation_id] = payload
      }
    }
    for (const id of serverIds.keys()) {
      if (!localIds.has(id)) delete_ids.push(id)
    }

    try {
      const res = await api.saveAnnotations(imageSetId, {
        author: this.state.user,
        message,
        base_version: this.state.version,
        upserts,
        update_ids,
        delete_ids,
      })
      this.state.status = `已保存为版本 v${res.version}`
      await this.loadAnnotations()
      await this.loadVersions()
    } catch (err) {
      if (err.status === 409) {
        this.state.status = '版本冲突：他人已提交，已拉取最新标注，请确认后重新保存'
        await this.loadAnnotations()
      } else {
        throw err
      }
    }
  }

  async loadVersions() {
    this.state.versions = await api.listVersions(this.state.imageSet.image_set_id)
  }

  async rollback(targetVersion) {
    const res = await api.rollback(this.state.imageSet.image_set_id, {
      author: this.state.user,
      target_version: targetVersion,
    })
    this.state.status = `已回滚到 v${targetVersion}（生成新版本 v${res.version}）`
    await this.loadAnnotations()
    await this.loadVersions()
  }

  _startPolling() {
    this._stopPolling()
    this._pollTimer = setInterval(async () => {
      if (!this.state.imageSet || this.state.dirty) return
      try {
        const res = await api.pollAnnotations(
          this.state.imageSet.image_set_id,
          this.state.version
        )
        if (res.changed) {
          this._serverAnnotations = res.annotations
          this.state.annotations = [...res.annotations]
          this.state.version = res.version
          this.state.status = '已同步其他用户的标注更新'
        }
      } catch {
        /* 网络抖动时静默，下轮重试 */
      }
    }, POLL_INTERVAL_MS)
  }

  _stopPolling() {
    if (this._pollTimer) clearInterval(this._pollTimer)
    this._pollTimer = null
  }
}
