/**
 * annotation_layer — 覆盖在 OSD 上的 SVG 标注层。
 * 支持多边形圈选病害区域（起甲/酥碱/霉变），选中、删除。
 * 坐标统一以图像像素存储，渲染时经 viewer_core 转换。
 */
export const LABELS = {
  flaking: { zh: '起甲', color: '#ff8c1a' },
  powdering: { zh: '酥碱', color: '#19c3e6' },
  mold: { zh: '霉变', color: '#e64fd0' },
}

const SVG_NS = 'http://www.w3.org/2000/svg'

export class AnnotationLayer {
  /**
   * @param {HTMLElement} container OSD 容器（position:relative）
   * @param {import('./viewer_core').ViewerCore} core
   */
  constructor(container, core) {
    this.core = core
    this.annotations = []
    this.draft = []
    this.mode = 'pan' // 'pan' | 'draw'
    this.activeLabel = 'flaking'
    this.selectedId = null
    this.onChange = null // (annotations) => void

    this.svg = document.createElementNS(SVG_NS, 'svg')
    this.svg.setAttribute('style',
      'position:absolute;inset:0;width:100%;height:100%;pointer-events:none;z-index:10;')
    container.appendChild(this.svg)

    container.addEventListener('click', (e) => this._onClick(e))
    container.addEventListener('dblclick', (e) => this._onDblClick(e))
    core.onViewportChange(() => this.render())
  }

  setMode(mode) {
    this.mode = mode
    this.core.setMouseNavEnabled(mode === 'pan')
    if (mode === 'pan') this.draft = []
    this.render()
  }

  setLabel(label) {
    this.activeLabel = label
  }

  setAnnotations(list) {
    this.annotations = list
    this.selectedId = null
    this.render()
  }

  deleteSelected() {
    if (!this.selectedId) return
    this.annotations = this.annotations.filter(
      (a) => a.annotation_id !== this.selectedId
    )
    this.selectedId = null
    this.render()
    this.onChange?.(this.annotations)
  }

  _onClick(e) {
    if (this.mode !== 'draw') return
    const rect = this.svg.getBoundingClientRect()
    const img = this.core.viewerToImage({
      x: e.clientX - rect.left,
      y: e.clientY - rect.top,
    })
    this.draft.push(img)
    this.render()
  }

  _onDblClick(e) {
    if (this.mode !== 'draw' || this.draft.length < 3) return
    e.preventDefault()
    const annotation = {
      annotation_id: `local-${Date.now()}`,
      label: this.activeLabel,
      geometry: { type: 'polygon', points: [...this.draft] },
      note: '',
      _local: true,
    }
    this.annotations.push(annotation)
    this.draft = []
    this.render()
    this.onChange?.(this.annotations)
  }

  _pointsToString(points) {
    return points
      .map((p) => {
        const v = this.core.imageToViewer(p)
        return `${v.x},${v.y}`
      })
      .join(' ')
  }

  render() {
    this.svg.innerHTML = ''
    for (const ann of this.annotations) {
      const color = LABELS[ann.label]?.color || '#fff'
      const poly = document.createElementNS(SVG_NS, 'polygon')
      poly.setAttribute('points', this._pointsToString(ann.geometry.points))
      poly.setAttribute('fill', color + '44')
      poly.setAttribute('stroke', color)
      poly.setAttribute('stroke-width',
        ann.annotation_id === this.selectedId ? '3' : '1.5')
      poly.setAttribute('style', 'pointer-events:stroke;cursor:pointer;')
      poly.addEventListener('click', (e) => {
        if (this.mode !== 'pan') return
        e.stopPropagation()
        this.selectedId = ann.annotation_id
        this.render()
      })
      this.svg.appendChild(poly)
    }
    if (this.draft.length) {
      const color = LABELS[this.activeLabel].color
      const polyline = document.createElementNS(SVG_NS, 'polyline')
      polyline.setAttribute('points', this._pointsToString(this.draft))
      polyline.setAttribute('fill', 'none')
      polyline.setAttribute('stroke', color)
      polyline.setAttribute('stroke-dasharray', '4 3')
      polyline.setAttribute('stroke-width', '2')
      this.svg.appendChild(polyline)
    }
  }
}
