import axios from 'axios'

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
  withCredentials: true,
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.request.use(config => {
  if (typeof window !== 'undefined') {
    const token = localStorage.getItem('edu_token')
    if (token) config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  res => res,
  err => {
    if (err.response?.status === 401 && typeof window !== 'undefined') {
      localStorage.removeItem('edu_token')
      localStorage.removeItem('edu_user')
      window.location.href = '/login'
    }
    // 428 Precondition Required is the backend's way of saying "the
    // current user still has a stale default password; block everything
    // until they change it." Hijack the browser to the forced-change
    // screen so the redirect is not something the UI can accidentally
    // skip. See backend/app/middleware/auth.py::require_current_password.
    if (err.response?.status === 428 && typeof window !== 'undefined') {
      if (!window.location.pathname.startsWith('/change-password')) {
        window.location.href = '/change-password'
      }
    }
    return Promise.reject(err)
  }
)

export default api
