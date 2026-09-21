/**
 * project_manager：项目与图像集的领域中枢。
 * 统一管理项目列表、当前图像集、标注集合、乐观锁版本，
 * 并桥接 WebSocket 协作事件，供各 Vue 组件复用。
 */
import { annotationApi, projectApi, uploadApi } from '@/api'
import { CollaborationClient } from '@/api/collaboration'

export class ProjectManager {
  constructor() {
    this.projects = []
    this.currentProject = null
    this.imagesets = []
    this.currentImageset = null
    this.annotations = []
    this.versions = []
    this.baseVersion = null
    this.onlineUsers = []
    this.collaboration = null
    this.listeners = new Set()
  }

  subscribe(listener) {
    this.listeners.add(listener)
    return () => this.listeners.delete(listener)
  }

  _notify() {
    this.listeners.forEach((listener) => listener())
  }

  async loadProjects() {
    this.projects = await projectApi.list()
    this._notify()
    return this.projects
  }

  async createProject(payload) {
    const project = await projectApi.create(payload)
    await this.loadProjects()
    return project
  }

  async openProject(projectId) {
    this.currentProject = await projectApi.get(projectId)
    this.imagesets = await projectApi.imagesets(projectId)
    this._notify()
  }

  async refreshImageset() {
    if (!this.currentProject || !this.currentImageset) return
    this.currentImageset = await projectApi.getImageset(
      this.currentProject.id,
      this.currentImageset.id,
    )
    this._notify()
  }

  async uploadImageset(files, title, onProgress) {
    const imageset = await uploadApi.createImageset(this.currentProject.id, {
      title,
      visible: files.visible,
      ir: files.ir,
      uv: files.uv,
    }, onProgress)
    this.imagesets = [imageset, ...this.imagesets]
    this._notify()
    return imageset
  }

  async openImageset(imagesetId) {
    this.collaboration?.close()
    this.currentImageset = this.imagesets.find((item) => item.id === imagesetId)
    this.annotations = await annotationApi.list(imagesetId)
    this.versions = await annotationApi.versions(imagesetId)
    this.baseVersion = this.versions[0]?.version ?? 0
    this._connectCollaboration(imagesetId)
    this._notify()
  }

  _connectCollaboration(imagesetId) {
    this.collaboration = new CollaborationClient(imagesetId, {
      annotation_created: ({ annotation }) => this._upsert(annotation),
      annotation_updated: ({ annotation }) => this._upsert(annotation),
      annotation_deleted: ({ annotation_id }) => this._remove(annotation_id),
      version_committed: () => this._reloadVersions(),
      rolled_back: (message) => {
        this.annotations = message.annotations
        this.baseVersion = message.new_version
        this._reloadVersions()
      },
      presence: (message) => {
        this.onlineUsers = message.users
        this._notify()
      },
      cursor: (message) => {
        if (typeof message.x === 'number' && typeof message.y === 'number') {
          this.cursorHandler?.(message.username, { x: message.x, y: message.y })
        }
      },
      imageset_status: async (message) => {
        await this.refreshImageset()
        this.statusHandler?.(message.status)
      },
    })
    this.collaboration.connect()
  }

  onCursor(handler) {
    this.cursorHandler = handler
  }

  onStatusChange(handler) {
    this.statusHandler = handler
  }

  sendCursor(point) {
    if (point) this.collaboration?.sendCursor(point.x, point.y)
  }

  _upsert(annotation) {
    const index = this.annotations.findIndex((item) => item.id === annotation.id)
    if (index >= 0) this.annotations.splice(index, 1, annotation)
    else this.annotations.push(annotation)
    this._notify()
  }

  _remove(annotationId) {
    this.annotations = this.annotations.filter((item) => item.id !== annotationId)
    this._notify()
  }

  async _reloadVersions() {
    if (!this.currentImageset) return
    this.versions = await annotationApi.versions(this.currentImageset.id)
    this.baseVersion = this.versions[0]?.version ?? this.baseVersion
    this._notify()
  }

  async createAnnotation(payload) {
    const created = await annotationApi.create(this.currentImageset.id, payload, this.baseVersion)
    this._upsert(created)
    return created
  }

  async updateAnnotation(id, payload) {
    const updated = await annotationApi.update(this.currentImageset.id, id, payload, this.baseVersion)
    this._upsert(updated)
    return updated
  }

  async deleteAnnotation(id) {
    await annotationApi.remove(this.currentImageset.id, id, this.baseVersion)
    this._remove(id)
  }

  async commitVersion(comment) {
    const { version } = await annotationApi.commit(this.currentImageset.id, comment)
    this.baseVersion = version
    await this._reloadVersions()
    return version
  }

  async rollback(version, comment) {
    const result = await annotationApi.rollback(this.currentImageset.id, version, comment)
    this.annotations = result.annotations
    this.baseVersion = result.new_version
    await this._reloadVersions()
  }

  dispose() {
    this.collaboration?.close()
  }
}

export const projectManager = new ProjectManager()
