/**
 * annotation_layer：在 OpenSeadragon 之上的 SVG 病害标注层。
 * 所有几何坐标以“原图像素”存储，渲染时经 viewer_core 实时换算，
 * 因此缩放/平移后标注始终与壁画精确对齐。
 */
import { diseaseColor } from '@/constants'

const SVG_NS = 'http://www.w3.org/2000/svg'

export class AnnotationLayer {
  constructor(viewerCore, container, callbacks = {}) {
    this.viewer = viewerCore
    this.callbacks = callbacks
    this.annotations = []
    this.tool = 'select' // select | polygon | rectangle
    this.diseaseType = 'flaking'
    this.selectedId = null
    this.draftPoints = []
    this.draftStart = null
    this.cursors = new Map()

    this.svg = document.createElementNS(SVG_NS, 'svg')
    this.svg.classList.add('annotation-layer')
    this.polygonGroup = document.createElementNS(SVG_NS, 'g')
    this.cursorGroup = document.createElementNS(SVG_NS, 'g')
    this.svg.append(this.polygonGroup, this.cursorGroup)
    container.appendChild(this.svg)

    this._bindViewerEvents()
    this.render()
  }

  setTool(tool) {
    this.tool = tool
    this.draftPoints = []
    this.draftStart = null
    this.viewer.setMouseNavEnabled(tool === 'select')
    this.render()
  }

  setDiseaseType(type) {
    this.diseaseType = type
  }

  setAnnotations(list) {
    this.annotations = list
    this.render()
  }

  upsertAnnotation(annotation) {
    const index = this.annotations.findIndex((item) => item.id === annotation.id)
    if (index >= 0) this.annotations.splice(index, 1, annotation)
    else this.annotations.push(annotation)
    this.render()
  }

  removeAnnotation(id) {
    this.annotations = this.annotations.filter((item) => item.id !== id)
    if (this.selectedId === id) this.selectedId = null
    this.render()
  }

  getSelected() {
    return this.annotations.find((item) => item.id === this.selectedId) || null
  }

  _bindViewerEvents() {
    this.viewer.on('canvas-press', (event) => {
      if (this.tool === 'select') return
      const point = this.viewer.viewerToImage(event.position)
      if (!point) return
      if (this.tool === 'polygon') {
        this.draftPoints.push(point)
      } else if (this.tool === 'rectangle') {
        this.draftStart = point
      }
      this.render()
    })

    this.viewer.on('canvas-drag', (event) => {
      if (this.tool !== 'rectangle' || !this.draftStart) return
      this._hoverPoint = this.viewer.viewerToImage(event.position)
      this.render()
    })

    this.viewer.on('canvas-release', () => {
      if (this.tool === 'rectangle' && this.draftStart && this._hoverPoint) {
        const coordinates = this._rectangleCoordinates(this.draftStart, this._hoverPoint)
        if (coordinates.length === 4) this.callbacks.onCreate?.(this._geometry('rectangle', coordinates))
        this.draftStart = null
        this._hoverPoint = null
        this.render()
      }
    })

    this.viewer.on('canvas-click', (event) => {
      if (this.tool !== 'polygon') {
        if (this.tool === 'select') this._handleSelectClick(event.position)
        return
      }
      // 双击起点附近完成多边形
      if (event.quick && this.draftPoints.length >= 3) {
        const current = this.viewer.viewerToImage(event.position)
        const first = this.draftPoints[0]
        if (Math.hypot(current.x - first.x, current.y - first.y) < 12) {
          this.callbacks.onCreate?.(this._geometry('polygon', this.draftPoints))
          this.draftPoints = []
          this.render()
        }
      }
    })

    this.viewer.on('animation', () => this.render())
    this.viewer.viewer.addHandler('update-viewport', () => this.render())
  }

  finishPolygon() {
    if (this.tool === 'polygon' && this.draftPoints.length >= 3) {
      this.callbacks.onCreate?.(this._geometry('polygon', this.draftPoints))
      this.draftPoints = []
      this.render()
    }
  }

  cancelDraft() {
    this.draftPoints = []
    this.draftStart = null
    this._hoverPoint = null
    this.render()
  }

  _geometry(type, points) {
    return { type, coordinates: points.map((p) => [p.x, p.y]) }
  }

  _rectangleCoordinates(start, end) {
    if (Math.abs(end.x - start.x) < 3 || Math.abs(end.y - start.y) < 3) return []
    return [
      [start.x, start.y],
      [end.x, start.y],
      [end.x, end.y],
      [start.x, end.y],
    ]
  }

  _handleSelectClick(position) {
    const imagePoint = this.viewer.viewerToImage(position)
    if (!imagePoint) return
    let hit = null
    for (const annotation of [...this.annotations].reverse()) {
      if (this._pointInGeometry(imagePoint, annotation.geometry)) {
        hit = annotation.id
        break
      }
    }
    this.selectedId = hit
    this.callbacks.onSelect?.(this.getSelected())
    this.render()
  }

  _pointInGeometry(point, geometry) {
    const polygon = geometry.type === 'rectangle'
      ? geometry.coordinates
      : geometry.coordinates
    if (geometry.type === 'point') {
      const [x, y] = geometry.coordinates[0]
      return Math.hypot(point.x - x, point.y - y) < 14
    }
    let inside = false
    for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
      const [xi, yi] = polygon[i]
      const [xj, yj] = polygon[j]
      const intersect =
        yi > point.y !== yj > point.y &&
        point.x < ((xj - xi) * (point.y - yi)) / (yj - yi) + xi
      if (intersect) inside = !inside
    }
    return inside
  }

  setRemoteCursor(username, imagePoint) {
    if (imagePoint) this.cursors.set(username, imagePoint)
    else this.cursors.delete(username)
    this.render()
  }

  render() {
    this.polygonGroup.innerHTML = ''
    for (const annotation of this.annotations) {
      this.polygonGroup.appendChild(this._renderShape(annotation))
    }
    const draft = this._renderDraft()
    if (draft) this.polygonGroup.appendChild(draft)

    this.cursorGroup.innerHTML = ''
    for (const [username, point] of this.cursors) {
      const projected = this.viewer.imageToViewer(point.x, point.y)
      if (!projected) continue
      const circle = document.createElementNS(SVG_NS, 'circle')
      circle.setAttribute('cx', projected.x)
      circle.setAttribute('cy', projected.y)
      circle.setAttribute('r', 6)
      circle.setAttribute('fill', '#2f80ed')
      circle.setAttribute('opacity', '0.8')
      const label = document.createElementNS(SVG_NS, 'text')
      label.setAttribute('x', projected.x + 9)
      label.setAttribute('y', projected.y + 4)
      label.setAttribute('class', 'cursor-label')
      label.textContent = username
      this.cursorGroup.append(circle, label)
    }
  }

  _renderShape(annotation) {
    const color = diseaseColor(annotation.disease_type)
    const points = this._projectCoordinates(annotation.geometry.coordinates)
    const group = document.createElementNS(SVG_NS, 'g')
    group.setAttribute('class', 'annotation-shape')

    if (annotation.geometry.type === 'point') {
      const [p] = points
      const circle = document.createElementNS(SVG_NS, 'circle')
      circle.setAttribute('cx', p.x)
      circle.setAttribute('cy', p.y)
      circle.setAttribute('r', 7)
      circle.setAttribute('fill', color)
      group.appendChild(circle)
    } else {
      const polygon = document.createElementNS(SVG_NS, 'polygon')
      polygon.setAttribute('points', points.map((p) => `${p.x},${p.y}`).join(' '))
      polygon.setAttribute('fill', color)
      polygon.setAttribute('fill-opacity', annotation.id === this.selectedId ? 0.35 : 0.18)
      polygon.setAttribute('stroke', color)
      polygon.setAttribute('stroke-width', annotation.id === this.selectedId ? 3 : 2)
      polygon.setAttribute('vector-effect', 'non-scaling-stroke')
      group.appendChild(polygon)
    }
    return group
  }

  _renderDraft() {
    let coordinates = []
    if (this.tool === 'polygon' && this.draftPoints.length > 0) {
      coordinates = this.draftPoints
    } else if (this.tool === 'rectangle' && this.draftStart && this._hoverPoint) {
      coordinates = [
        this.draftStart,
        { x: this._hoverPoint.x, y: this.draftStart.y },
        this._hoverPoint,
        { x: this.draftStart.x, y: this._hoverPoint.y },
      ]
    }
    if (coordinates.length === 0) return null
    const points = this._projectCoordinates(coordinates)
    const polygon = document.createElementNS(SVG_NS, 'polygon')
    polygon.setAttribute('points', points.map((p) => `${p.x},${p.y}`).join(' '))
    polygon.setAttribute('fill', diseaseColor(this.diseaseType))
    polygon.setAttribute('fill-opacity', '0.25')
    polygon.setAttribute('stroke', diseaseColor(this.diseaseType))
    polygon.setAttribute('stroke-dasharray', '6 4')
    polygon.setAttribute('stroke-width', 2)
    polygon.setAttribute('vector-effect', 'non-scaling-stroke')
    return polygon
  }

  _projectCoordinates(coordinates) {
    return coordinates
      .map(([x, y]) => this.viewer.imageToViewer(x, y))
      .filter(Boolean)
  }

  destroy() {
    this.svg.remove()
  }
}
