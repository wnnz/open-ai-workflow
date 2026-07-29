import axios from 'axios'

const api = axios.create({ baseURL: '/api/v1', timeout: 30000 })
api.interceptors.request.use(config => {
  const token = localStorage.getItem('access_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})
api.interceptors.response.use(response => response, error => {
  if (error.response?.status === 401) {
    localStorage.removeItem('access_token'); localStorage.removeItem('user')
    if (location.pathname !== '/login') {
      const returnTo = `${location.pathname}${location.search}${location.hash}`
      location.assign(`/login?redirect=${encodeURIComponent(returnTo)}`)
    }
  }
  return Promise.reject(error)
})
export default api
