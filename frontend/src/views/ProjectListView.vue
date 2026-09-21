<template>
  <div class="page">
    <header class="topbar">
      <h2>壁画项目</h2>
      <div class="user-box">
        <span>{{ auth.user?.display_name }}</span>
        <button class="btn" @click="logout">退出</button>
      </div>
    </header>

    <main class="content">
      <section class="create-box">
        <input v-model="newProject.name" placeholder="新项目名称，如：莫高窟第 257 窟" @keyup.enter="createProject" />
        <input v-model="newProject.description" placeholder="项目描述（可选）" />
        <button class="btn primary" @click="createProject">创建项目</button>
      </section>

      <div v-if="error" class="error">{{ error }}</div>

      <section class="project-grid">
        <RouterLink
          v-for="project in projects"
          :key="project.id"
          :to="`/projects/${project.id}`"
          class="project-card"
        >
          <h3>{{ project.name }}</h3>
          <p>{{ project.description || '暂无描述' }}</p>
          <footer>
            <span>成员 {{ project.members.length }} 人</span>
            <span>{{ formatDate(project.created_at) }}</span>
          </footer>
        </RouterLink>
      </section>
    </main>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'

import { useAuthStore } from '@/stores/auth'
import { projectManager } from '@/modules/project_manager/project_manager'

const auth = useAuthStore()
const router = useRouter()
const projects = ref([])
const error = ref('')
const newProject = reactive({ name: '', description: '' })

onMounted(async () => {
  projects.value = await projectManager.loadProjects()
})

async function createProject() {
  if (!newProject.name.trim()) return
  try {
    await projectManager.createProject({ name: newProject.name, description: newProject.description })
    projects.value = projectManager.projects
    newProject.name = ''
    newProject.description = ''
  } catch (err) {
    error.value = err.response?.data?.detail || '创建失败'
  }
}

function logout() {
  auth.logout()
  router.push('/login')
}

function formatDate(value) {
  return new Date(value).toLocaleDateString('zh-CN')
}
</script>

<style scoped>
.page { min-height: 100vh; }
.topbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 28px;
  border-bottom: 1px solid var(--border);
  background: var(--panel);
}
.topbar h2 { margin: 0; color: var(--accent); }
.user-box { display: flex; align-items: center; gap: 12px; color: var(--text-dim); }
.content { max-width: 1100px; margin: 0 auto; padding: 28px; }
.create-box {
  display: grid;
  grid-template-columns: 1.4fr 2fr auto;
  gap: 10px;
  margin-bottom: 28px;
}
.project-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}
.project-card {
  display: block;
  padding: 20px;
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: 10px;
  text-decoration: none;
  color: var(--text);
  transition: border-color 0.15s, transform 0.15s;
}
.project-card:hover {
  border-color: var(--accent);
  transform: translateY(-2px);
}
.project-card h3 { margin: 0 0 8px; }
.project-card p { color: var(--text-dim); font-size: 13px; min-height: 38px; }
.project-card footer {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: var(--text-dim);
}
.error { color: var(--danger); margin-bottom: 12px; }
</style>
