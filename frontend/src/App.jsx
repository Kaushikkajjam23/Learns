// src/App.jsx
import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import Login from './components/Auth/Login';
import Register from './components/Auth/Register';
import ResetPassword from './components/Auth/ResetPassword';
import Dashboard from './components/Dashboard/Dashboard';
import TopicForm from './components/TopicForm';
import LearningPathDetail from './components/LearningPath/LearningPathDetail';
import DocumentUploadPage from './components/DocumentUpload/DocumentUploadPage';
import DocumentReviewPage from './components/DocumentUpload/DocumentReviewPage';
import AssignLearningPathsPage from './components/DocumentUpload/AssignLearningPathsPage';
import NotFound from './components/NotFound';
import './App.css';

// Protected route component for authenticated users
const ProtectedRoute = ({ children }) => {
  const { isAuthenticated, loading } = useAuth();
  
  if (loading) {
    return <div className="loading">Loading authentication status...</div>;
  }
  
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }
  
  return children;
};

// Manager only route component
const ManagerRoute = ({ children }) => {
  const { isAuthenticated, loading, user } = useAuth();
  
  if (loading) {
    return <div className="loading">Loading authentication status...</div>;
  }
  
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }
  
  if (user?.role !== 'manager') {
    return <Navigate to="/dashboard" replace />;
  }
  
  return children;
};

function App() {
  return (
    <AuthProvider>
      <Router>
        <div className="app-container">
          <Routes>
            {/* Public routes */}
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
            <Route path="/reset-password" element={<ResetPassword />} />
            
            {/* Protected routes for authenticated users */}
            <Route 
              path="/dashboard" 
              element={
                <ProtectedRoute>
                  <Dashboard />
                </ProtectedRoute>
              } 
            />
            
            <Route 
              path="/create-path" 
              element={
                <ProtectedRoute>
                  <TopicForm />
                </ProtectedRoute>
              } 
            />
            
            <Route 
              path="/learning-path/:pathId" 
              element={
                <ProtectedRoute>
                  <LearningPathDetail />
                </ProtectedRoute>
              } 
            />
            
            {/* Manager-only routes */}
            <Route 
              path="/document-upload" 
              element={
                <ManagerRoute>
                  <DocumentUploadPage />
                </ManagerRoute>
              } 
            />
            
            <Route 
              path="/document-review" 
              element={
                <ManagerRoute>
                  <DocumentReviewPage />
                </ManagerRoute>
              } 
            />
            
            <Route 
              path="/assign-learning-paths" 
              element={
                <ManagerRoute>
                  <AssignLearningPathsPage />
                </ManagerRoute>
              } 
            />
            
            {/* Redirect and fallback routes */}
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route path="*" element={<NotFound />} />
          </Routes>
        </div>
      </Router>
    </AuthProvider>
  );
}

export default App;