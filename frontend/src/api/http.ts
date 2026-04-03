import axios from 'axios'
import { useAuthStore } from '@/stores/auth'

const http = axios.create({
  timeout: 60000,
})

http.interceptors.request.use((config) => {
  const auth = useAuthStore()
  if (auth.token) {
    config.headers.Authorization = `Bearer ${auth.token}`
  }
  return config
})

export default http
