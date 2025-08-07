import axios from 'axios';
import { LoginData, RegisterData, ProfileUpdateData, User } from '../types/user';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8080';

// Create axios instance with default config
const api = axios.create({
  baseURL: `${API_BASE_URL}/api/`,
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add CSRF token to requests
let csrfToken: string | null = null;

// Function to get CSRF token
export const getCSRFToken = async (): Promise<string> => {
  try {
    const response = await api.get<{ csrfToken: string }>('auth/csrf/');
    csrfToken = response.data.csrfToken;
    return csrfToken;
  } catch (error) {
    console.error('Failed to get CSRF token:', error);
    throw error;
  }
};

// Add CSRF token interceptor
api.interceptors.request.use(
  (config) => {
    if (['post', 'put', 'patch', 'delete'].includes(config.method?.toLowerCase() || '')) {
      if (csrfToken && config.headers) {
        config.headers['X-CSRFToken'] = csrfToken;
      }
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Helper function to ensure CSRF token is available
const ensureCSRFToken = async (): Promise<void> => {
  if (!csrfToken) {
    try {
      await getCSRFToken();
    } catch (error) {
      console.error('Could not get CSRF token:', error);
    }
  }
};

// Authentication API
export const authAPI = {
  login: async (data: LoginData): Promise<{ message: string; user: User }> => {
    await ensureCSRFToken();
    const response = await api.post<{ message: string; user: User }>('auth/login/', data);
    return response.data;
  },

  register: async (data: RegisterData): Promise<{ message: string; user: User }> => {
    await ensureCSRFToken();
    const response = await api.post<{ message: string; user: User }>('auth/register/', data);
    return response.data;
  },

  logout: async (): Promise<{ message: string }> => {
    await ensureCSRFToken();
    const response = await api.post<{ message: string }>('auth/logout/');
    return response.data;
  },

  getUserInfo: async (): Promise<{ user: User }> => {
    const response = await api.get<{ user: User }>('auth/user/');
    return response.data;
  },
};

// Profile API
export const profileAPI = {
  getProfile: async (): Promise<{ user: User }> => {
    const response = await api.get<{ user: User }>('profile/');
    return response.data;
  },

  updateProfile: async (data: ProfileUpdateData): Promise<{ message: string; user: User }> => {
    await ensureCSRFToken();
    const response = await api.put<{ message: string; user: User }>('profile/update/', data);
    return response.data;
  },
};

export default api;
