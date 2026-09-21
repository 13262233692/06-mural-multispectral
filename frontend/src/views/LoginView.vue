<template>
  <div class="login-page">
    <div class="login-card">
      <h1>敦煌壁画多光谱<br />图像处理平台</h1>
      <div class="tabs">
        <button :class="{ active: mode === 'login' }" @click="mode = 'login'">登录</button>
        <button :class="{ active: mode === 'register' }" @click="mode = 'register'">注册</button>
      </div>
      <form @submit.prevent="submit">
        <div v-if="mode === 'register'" class="field">
          <label>显示名称</label>
          <input v-model="form.display_name" placeholder="如：张修复师" />
        </div>
        <div class="field">
          <label>用户名</label>
          <input v-model="form.username" required autocomplete="username" />
        </div>
        <div class="field">
          <label>密码</label>
          <input v-model="form.password" type="password" required autocomplete="current-password" />
        </div>
        <p v-if="error" class="error">{{ error }}</p>
        <button class="btn primary" type="submit" style="width: 100%">{{ loading ? '请稍候…' : '进入平台' }}</button>
      </form>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'

import { useAuthStore } from '@/stores/auth'

const mode = ref('login')
const loading = ref(false)
const error = ref('')
const form = reactive({ username: '', password: '', display_name: '' })
const auth = useAuthStore()
const router = useRouter()

async function submit() {
  loading.value = true
  error.value = ''
  try {
    if (mode.value === 'login') await auth.login(form)
    else await auth.register(form)
    router.push('/projects')
  } catch (err) {
    error.value = err.response?.data?.detail || '操作失败'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: grid;
  place-items: center;
  background: radial-gradient(circle at 30% 20%, #3a2c1d, #1d1b18);
}
.login-card {
  width: 380px;
  padding: 32px;
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: 12px;
}
h1 {
  font-size: 22px;
  line-height: 1.5;
  text-align: center;
  margin: 0 0 24px;
  color: var(--accent);
}
.tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 20px;
}
.tabs button {
  flex: 1;
  padding: 8px;
  background: transparent;
  border: 1px solid var(--border);
  border-radius: 6px;
  color: var(--text-dim);
  cursor: pointer;
}
.tabs button.active {
  background: var(--accent);
  color: #1d1b18;
  border-color: var(--accent);
}
.error {
  color: var(--danger);
  font-size: 13px;
}
</style>
