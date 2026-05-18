import axios from 'axios'

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 60000,
})

// Chat — 唯一入口
export function sendChat(query: string) {
  return api.post('/chat', { query })
}

export default api
