import axios, { type AxiosError } from 'axios'
import type { ApiError } from '@/types'

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api/v1'

// Create axios instance with credentials for httpOnly cookies
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true,
})

// Response interceptor - handle 401 and token refresh via cookies
let isRefreshing = false
let failedQueue: Array<{
  resolve: () => void
  reject: (error: unknown) => void
}> = []

const processQueue = (error: unknown) => {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error)
    } else {
      prom.resolve()
    }
  })
  failedQueue = []
}

apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError<ApiError>) => {
    const originalRequest = error.config

    // If 401 and not already retrying, try to refresh via cookie
    if (error.response?.status === 401 && originalRequest && !originalRequest.headers['X-Retry']) {
      if (isRefreshing) {
        // Wait for the refresh to complete
        return new Promise((resolve, reject) => {
          failedQueue.push({
            resolve: () => resolve(apiClient(originalRequest)),
            reject,
          })
        })
      }

      isRefreshing = true
      originalRequest.headers['X-Retry'] = 'true'

      try {
        // Call refresh endpoint — cookie sent automatically
        await axios.post(`${API_BASE_URL}/auth/refresh`, null, {
          withCredentials: true,
        })

        processQueue(null)

        return apiClient(originalRequest)
      } catch (refreshError) {
        processQueue(refreshError)
        // Redirect to login will be handled by the auth store
        return Promise.reject(refreshError)
      } finally {
        isRefreshing = false
      }
    }

    return Promise.reject(error)
  }
)

export default apiClient
