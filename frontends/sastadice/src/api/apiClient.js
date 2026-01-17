/**
 * API client with Axios interceptors for error handling
 */
import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://api.sastaspace.com/api/v1'

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 10000,
})

// Request interceptor
apiClient.interceptors.request.use(
  (config) => {
    // Add auth token if available
    // const token = localStorage.getItem('auth_token')
    // if (token) {
    //   config.headers.Authorization = `Bearer ${token}`
    // }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response) {
      // Server responded with error status
      const { status, data } = error.response
      
      if (status === 404) {
        console.error('Resource not found:', error.config.url)
      } else if (status === 401) {
        console.error('Unauthorized - please login')
        // Handle logout
      } else if (status === 500) {
        console.error('Server error:', data.message || 'Internal server error')
      }
    } else if (error.request) {
      // Request made but no response
      console.error('Network error:', error.message)
    } else {
      // Something else happened
      console.error('Error:', error.message)
    }
    
    return Promise.reject(error)
  }
)

export default apiClient
