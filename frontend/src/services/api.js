import axios from 'axios';

// In Docker environment, use nginx proxy for API calls
const API_BASE_URL = '/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to include CSRF token
api.interceptors.request.use(
  (config) => {
    const csrfToken = document.cookie
      .split('; ')
      .find(row => row.startsWith('csrftoken='))
      ?.split('=')[1];
    
    if (csrfToken) {
      config.headers['X-CSRFToken'] = csrfToken;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor to handle errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    console.log('API Error:', error);
    if (error.response?.status === 401) {
      // Redirect to login if unauthorized
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export const authAPI = {
  login: (email, password) => 
    api.post('/accounts/login/', { email, password }),
  
  register: (email, password1, password2) => 
    api.post('/accounts/signup/', { email, password1, password2 }),
  
  logout: () => 
    api.post('/accounts/logout/'),
  
  getCurrentUser: () => 
    api.get('/users/'),
};

export const profileAPI = {
  onboard: (resumeFile, linkedinUrl) => {
    const formData = new FormData();
    formData.append('resume_file', resumeFile);
    formData.append('linkedin_url', linkedinUrl);
    
    return api.post('/profiles/onboard/', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
  },
};

export const portfolioAPI = {
  getMyPortfolio: () => 
    api.get('/portfolio/me/'),
  
  updateMyPortfolio: (data) => 
    api.put('/portfolio/me/', data),
  
  getPublicPortfolio: (slug) => 
    api.get(`/portfolio/public/${slug}/`),
};

export default api; 