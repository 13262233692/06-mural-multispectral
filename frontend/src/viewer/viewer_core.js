/**
 * viewer_core — OpenSeadragon 查看器封装。
 * 负责加载配准/融合结果图，提供 图像坐标 <-> 视口坐标 转换。
 */
import OpenSeadragon from 'openseadragon'

export class ViewerCore {
  constructor(elementId) {
    this.viewer = OpenSeadragon({
      id: elementId,
      prefixUrl: 'https://cdn.jsdelivr.net/npm/openseadragon@4.1/build/openseadragon/images/',
      showNavigationControl: true,
      maxZoomPixelRatio: 8,
      minZoomLevel: 0.5,
      visibilityRatio: 0.3,
      crossOriginPolicy: 'Anonymous',
    })
    this.imageWidth = 1
    this.imageHeight = 1
    this._viewportListeners = []
    this.viewer.addHandler('update-viewport', () => this._emitViewport())
    this.viewer.addHandler('open', () => {
      const item = this.viewer.world.getItemAt(0)
      if (item) {
        const { x, y } = item.getContentSize()
        this.imageWidth = x
        this.imageHeight = y
      }
      this._emitViewport()
    })
  }

  /** 加载融合结果图（后端静态目录）。 */
  openImage(url) {
    this.viewer.open({ type: 'image', url, buildPyramid: false })
  }

  onViewportChange(fn) {
    this._viewportListeners.push(fn)
  }

  _emitViewport() {
    for (const fn of this._viewportListeners) fn()
  }

  /** 图像像素坐标 -> 页面像素坐标（供 SVG overlay 使用）。 */
  imageToViewer(point) {
    const item = this.viewer.world.getItemAt(0)
    if (!item) return { x: 0, y: 0 }
    const vp = item.imageToViewerElementCoordinates(
      new OpenSeadragon.Point(point.x, point.y)
    )
    return { x: vp.x, y: vp.y }
  }

  /** 页面像素坐标 -> 图像像素坐标（标注落点）。 */
  viewerToImage(point) {
    const item = this.viewer.world.getItemAt(0)
    if (!item) return { x: 0, y: 0 }
    const img = item.viewerElementToImageCoordinates(
      new OpenSeadragon.Point(point.x, point.y)
    )
    return { x: img.x, y: img.y }
  }

  setMouseNavEnabled(enabled) {
    this.viewer.setMouseNavEnabled(enabled)
  }
}
