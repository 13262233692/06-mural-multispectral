<template>
  <div class="viewer-wrap">
    <div ref="viewerEl" class="osd-host" />
  </div>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'

import { ViewerCore } from '@/modules/viewer_core/viewer_core'
import { AnnotationLayer } from '@/modules/annotation_layer/annotation_layer'
import { projectManager } from '@/modules/project_manager/project_manager'

const props = defineProps({
  layers: { type: Object, default: () => ({}) },
  band: { type: String, default: 'fused' },
  tool: { type: String, default: 'select' },
  diseaseType: { type: String, default: 'flaking' },
})

const emit = defineEmits(['select', 'create'])
const viewerEl = ref(null)

let viewer = null
let layer = null
let cursorThrottle = 0

onMounted(async () => {
  viewer = new ViewerCore(viewerEl.value)
  layer = new AnnotationLayer(viewer, viewerEl.value, {
    onSelect: (annotation) => emit('select', annotation),
    onCreate: (geometry) => emit('create', geometry),
  })
  layer.setDiseaseType(props.diseaseType)
  layer.setAnnotations(projectManager.annotations)

  if (Object.keys(props.layers).length) {
    await viewer.loadLayers(props.layers, props.band)
  }

  // OpenSeadragon 无原生 mousemove 事件，用浏览器事件 + viewer 视口换算上报图像坐标
  viewerEl.value.addEventListener('mousemove', (event) => {
    const now = Date.now()
    if (now - cursorThrottle < 60) return
    cursorThrottle = now
    const rect = viewerEl.value.getBoundingClientRect()
    const point = viewer.viewerToImage({
      x: event.clientX - rect.left,
      y: event.clientY - rect.top,
    })
    if (point) projectManager.sendCursor(point)
  })

  projectManager.onCursor((username, point) => layer.setRemoteCursor(username, point))
})

watch(() => props.layers, async (layers) => {
  if (viewer && Object.keys(layers).length) {
    await viewer.loadLayers(layers, props.band)
    layer?.setAnnotations(projectManager.annotations)
  }
})

watch(() => props.band, async (band) => {
  if (viewer) await viewer.switchBand(band)
})

watch(() => props.tool, (tool) => layer?.setTool(tool))
watch(() => props.diseaseType, (type) => layer?.setDiseaseType(type))

watch(
  () => projectManager.annotations,
  (annotations) => layer?.setAnnotations(annotations),
  { deep: true },
)

function finishPolygon() {
  layer?.finishPolygon()
}

function cancelDraft() {
  layer?.cancelDraft()
}

defineExpose({ finishPolygon, cancelDraft })

onBeforeUnmount(() => {
  layer?.destroy()
  viewer?.destroy()
})
</script>

<style scoped>
.viewer-wrap {
  position: absolute;
  inset: 0;
}
.osd-host {
  position: absolute;
  inset: 0;
  background: #100f0d;
}
</style>
