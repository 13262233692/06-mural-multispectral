<template>
  <div class="viewer-toolbar">
    <div class="band-switch">
      <button
        v-for="bandOption in availableBands"
        :key="bandOption.key"
        class="btn tiny"
        :class="{ active: band === bandOption.key }"
        @click="$emit('switch-band', bandOption.key)"
      >
        {{ bandOption.label }}
      </button>
    </div>
    <div class="online">
      <span v-for="user in onlineUsers" :key="user" class="online-user">● {{ user }}</span>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

import { BANDS } from '@/constants'

const props = defineProps({
  layers: { type: Object, default: () => ({}) },
  band: String,
  onlineUsers: { type: Array, default: () => [] },
})
defineEmits(['switch-band'])

const availableBands = computed(() => BANDS.filter((item) => props.layers[item.key]))
</script>

<style scoped>
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
.online { display: flex; gap: 10px; font-size: 12px; color: #9fd0ff; }
</style>
