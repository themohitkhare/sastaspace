import axios from 'axios'

const getApiBaseUrl = () => {
  if (import.meta.env.VITE_API_URL) {
    return import.meta.env.VITE_API_URL
  }

  const hostname = window.location.hostname
  const port = window.location.port
  const protocol = window.location.protocol

  // When served through Traefik (port 80/443), use relative URL so requests
  // go through Traefik too — avoids CORS issues
  if (hostname === 'localhost' || hostname === '127.0.0.1') {
    if (!port || port === '80' || port === '443') {
      return '/api/v1'
    }
    return 'http://localhost:8000/api/v1'
  }

  return `${protocol}//${hostname}:8000/api/v1`
}

const API_BASE_URL = getApiBaseUrl()

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 10000,
})

export default apiClient
