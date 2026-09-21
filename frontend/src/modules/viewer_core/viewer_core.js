/**
 * viewer_core：OpenSeadragon 深度缩放查看器封装。
 * 负责多波段 DZI 图层切换、视口坐标换算、鼠标位置回调；
 * 不关心标注业务，保持与 annotation_layer 解耦。
 */
import OpenSeadragon from 'openseadragon'

export class ViewerCore {
  constructor(element, options = {}) {
    this.viewer = OpenSeadragon({
      element,
      // 使用随前端分发的本地图标，适配洞窟/内网无外网环境
      prefixUrl: '/osd-images/',
      showNavigationControl: true,
      navigationControlAnchor: OpenSeadragon.ControlAnchor.TOP_LEFT,
      gestureSettingsMouse: { clickToZoom: false },
      maxZoomPixelRatio: 4,
      ...options,
    })
    this.layers = {}
    this.activeBand = null
    this.imageWidth = 0
    this.imageHeight = 0
  }

  /** layersMeta: { fused: {dzi描述}, visible: {...}, ir: {...}, uv: {...} } */
  loadLayers(layersMeta, initialBand = 'fused') {
    this.layers = layersMeta
    this.activeBand = null
    const available = Object.keys(layersMeta)
    const band = available.includes(initialBand) ? initialBand : available[0]
    return this.switchBand(band)
  }

  switchBand(band) {
    const meta = this.layers[band]
    if (!meta) return Promise.resolve()
    if (this.activeBand === band && this.viewer.world.getItemCount() > 0) return Promise.resolve()

    this.activeBand = band
    this.imageWidth = meta.width
    this.imageHeight = meta.height
    return new Promise((resolve) => {
      this.viewer.open(meta)
      const item = this.viewer.world.getItemAt(0)
      if (item) {
        item.addOnceHandler('fully-loaded-change', resolve)
        setTimeout(resolve, 600)
      } else {
        setTimeout(resolve, 600)
      }
    })
  }

  /** 浏览器视口像素 -> 图像像素坐标 */
  viewerToImage(eventPosition) {
    const item = this.viewer.world.getItemAt(0)
    if (!item) return null
    const viewportPoint = this.viewer.viewport.pointFromPixel(eventPosition)
    const imagePoint = item.viewportToImageCoordinates(viewportPoint)
    return { x: Math.round(imagePoint.x), y: Math.round(imagePoint.y) }
  }

  /** 图像像素坐标 -> viewer 容器像素坐标（供标注覆盖层使用） */
  imageToViewer(imageX, imageY) {
    const item = this.viewer.world.getItemAt(0)
    if (!item) return null
    const viewportPoint = item.imageToViewportCoordinates(imageX, imageY)
    const pixel = this.viewer.viewport.pixelFromPoint(viewportPoint, true)
    return { x: pixel.x, y: pixel.y }
  }

  on(eventName, handler) {
    this.viewer.addHandler(eventName, handler)
  }

  setMouseNavEnabled(enabled) {
    this.viewer.setMouseNavEnabled(enabled)
  }

  destroy() {
    this.viewer.destroy()
  }
}
