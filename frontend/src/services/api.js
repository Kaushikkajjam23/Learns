// src/services/api.js

import axios from 'axios';

// Create axios instance with base URL
const api = axios.create({
  baseURL: 'http://localhost:8000',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add request interceptor to include auth token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers['Authorization'] = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Authentication API
const authAPI = {
  login: (credentials) => {
  console.log('API login called with:', credentials);
  
  // Create form data
  const formData = new URLSearchParams();
  formData.append('username', credentials.email);
  formData.append('password', credentials.password);
  
  // Send as form-urlencoded
  return axios.post('http://localhost:8000/token', formData, {
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
    }
  });
},
  register: (userData) => {
    return api.post('/api/auth/register', userData);
  },
  getCurrentUser: () => {
    return api.get('/api/auth/me');
  },
  logout: () => {
    localStorage.removeItem('token');
    return Promise.resolve();
  },
  requestPasswordReset: (email) => {
    return api.post('/api/auth/forgot-password', { email });
  },
  resetPassword: (token, newPassword) => {
    return api.post('/api/auth/reset-password', { 
      token, 
      new_password: newPassword 
    });
  }
};

// Learning Path API
const learningPathAPI = {
  createLearningPath: (topicData) => {
    return api.post('/api/learning-paths', topicData);
  },
  getLearningPaths: () => {
    return api.get('/api/learning-paths');
  },
  getLearningPath: (pathId) => {
    return api.get(`/api/learning-paths/${pathId}`);
  },
  updateLearningPath: (pathId, pathData) => {
    return api.put(`/api/learning-paths/${pathId}`, pathData);
  },
  deleteLearningPath: (pathId) => {
    return api.delete(`/api/learning-paths/${pathId}`);
  },
  updateSubtopicCompletion: (pathId, subtopicName, isCompleted) => {
    return api.post(`/api/learning-paths/${pathId}/subtopics/completion`, {
      subtopic_name: subtopicName,
      is_completed: isCompleted,
    });
  },
  getResources: (pathId, subtopicId) => {
    return api.get(`/api/learning-paths/${pathId}/subtopics/${subtopicId}/resources`);
  },
  addResource: (pathId, subtopicId, resourceData) => {
    return api.post(`/api/learning-paths/${pathId}/subtopics/${subtopicId}/resources`, resourceData);
  },
  getDetailedSubtopicContent: (pathId, subtopicId) => {
    return api.get(`/api/learning-paths/${pathId}/subtopics/${subtopicId}/detailed`);
  },
};

// Document Upload API
const documentAPI = {
  uploadDocument: (formData, progressCallback) => {
    return api.post('/api/documents/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      },
      onUploadProgress: progressCallback
    });
  },
  
  createLearningPathsFromDocument: (extractedData) => {
    return api.post('/api/documents/create-learning-paths', extractedData);
  },
  
  getRecentlyCreatedPaths: () => {
    return api.get('/api/documents/recent-paths');
  },
  
  assignLearningPaths: (assignments) => {
    return api.post('/api/documents/assign-paths', { assignments });
  }
};

// User API
const userAPI = {
  getAllEmployees: () => {
    return api.get('/api/users/employees');
  },
  updateProfile: (userData) => {
    return api.put('/api/users/profile', userData);
  }
};

// Export all API services
export const apiServices = {
  auth: authAPI,
  learningPath: learningPathAPI,
  document: documentAPI,
  user: userAPI
};

// Export individual services
export { api, authAPI, learningPathAPI, documentAPI, userAPI };

// Default export
export default {
  auth: authAPI,
  learningPath: learningPathAPI,
  document: documentAPI,
  user: userAPI
};