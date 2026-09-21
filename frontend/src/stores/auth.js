import { defineStore } from 'pinia'

import { authApi } from '@/api'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: localStorage.getItem('token') || '',
    user: null,
  }),
  getters: {
    isLoggedIn: (state) => Boolean(state.token),
  },
  actions: {
    setSession({ access_token, user }) {
      this.token = access_token
      this.user = user
      localStorage.setItem('token', access_token)
    },
    async login(payload) {
      this.setSession(await authApi.login(payload))
    },
    async register(payload) {
      this.setSession(await authApi.register(payload))
    },
    async fetchMe() {
      this.user = await authApi.me()
      return this.user
    },
    logout() {
      this.token = ''
      this.user = null
      localStorage.removeItem('token')
    },
  },
})
