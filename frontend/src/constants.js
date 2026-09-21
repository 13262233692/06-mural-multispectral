export const DISEASE_TYPES = [
  { value: 'flaking', label: '起甲', color: '#e8504a' },
  { value: 'efflorescence', label: '酥碱', color: '#f2b134' },
  { value: 'mold', label: '霉变', color: '#3aa55a' },
]

export const DISEASE_MAP = Object.fromEntries(DISEASE_TYPES.map((item) => [item.value, item]))

export const diseaseColor = (type) => DISEASE_MAP[type]?.color ?? '#9b59b6'
export const diseaseLabel = (type) => DISEASE_MAP[type]?.label ?? type

export const BANDS = [
  { key: 'fused', label: '伪彩融合' },
  { key: 'visible', label: '可见光' },
  { key: 'ir', label: '红外' },
  { key: 'uv', label: '紫外' },
]
