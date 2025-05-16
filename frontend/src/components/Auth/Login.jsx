// src/components/Auth/Login.jsx
import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { authAPI } from '../../services/api';
import './Auth.css';

const Login = () => {
  const [credentials, setCredentials] = useState({
    email: '',
    password: ''
  });
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [showForgotPassword, setShowForgotPassword] = useState(false);
  const [resetEmail, setResetEmail] = useState('');
  const [resetSuccess, setResetSuccess] = useState(null);
  const navigate = useNavigate();

  const handleChange = (e) => {
    const { name, value } = e.target;
    setCredentials(prev => ({
      ...prev,
      [name]: value
    }));
  };

  // In Login.jsx
const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      console.log('Attempting login with:', credentials);
      
      const response = await authAPI.login(credentials);
      console.log('Login response:', response);
      
      // Store token in localStorage
      localStorage.setItem('token', response.data.access_token);
      
      // Store user info if needed
      if (response.data.email) {
        localStorage.setItem('user_email', response.data.email);
        localStorage.setItem('user_id', response.data.user_id);
      }
      
      // Navigate to dashboard
      navigate('/dashboard');
    } catch (err) {
      console.error('Login error:', err);
      
      if (err.response && err.response.data) {
        console.log('Error response data:', err.response.data);
        setError(err.response.data.detail || 'Login failed. Please check your credentials.');
      } else {
        setError('Login failed. Please try again later.');
      }
    } finally {
      setLoading(false);
    }
};

  const handleForgotPassword = async (e) => {
    e.preventDefault();
    setError(null);
    setResetSuccess(null);
    setLoading(true);

    try {
      if (!resetEmail) {
        setError('Please enter your email address');
        setLoading(false);
        return;
      }

      // Call password reset API
      await authAPI.requestPasswordReset(resetEmail);
      
      // Show success message
      setResetSuccess('Password reset link sent to your email. Please check your inbox.');
      
      // Clear the email field
      setResetEmail('');
    } catch (err) {
      console.error('Password reset error:', err);
      
      if (err.response && err.response.data) {
        setError(err.response.data.detail || 'Failed to send reset link. Please try again.');
      } else {
        setError('Failed to send reset link. Please try again later.');
      }
    } finally {
      setLoading(false);
    }
  };

  const toggleForgotPassword = () => {
    setShowForgotPassword(!showForgotPassword);
    setError(null);
    setResetSuccess(null);
  };

  return (
    <div className="auth-container">
      <div className="auth-card">
        <h2>{showForgotPassword ? 'Reset Password' : 'Login'}</h2>
        
        {error && <div className="error-message">{error}</div>}
        {resetSuccess && <div className="success-message">{resetSuccess}</div>}
        
        {!showForgotPassword ? (
          // Login Form
          <form onSubmit={handleSubmit}>
            <div className="form-group">
              <label htmlFor="email">Email</label>
              <input
                type="email"
                id="email"
                name="email"
                value={credentials.email}
                onChange={handleChange}
                required
              />
            </div>
            
            <div className="form-group">
              <label htmlFor="password">Password</label>
              <input
                type="password"
                id="password"
                name="password"
                value={credentials.password}
                onChange={handleChange}
                required
              />
            </div>
            
            <button 
              type="submit" 
              className="auth-button"
              disabled={loading}
            >
              {loading ? 'Logging in...' : 'Login'}
            </button>
            
            <div className="auth-links">
              <button 
                type="button" 
                className="text-button"
                onClick={toggleForgotPassword}
              >
                Forgot Password?
              </button>
              <Link to="/register">Don't have an account? Register</Link>
            </div>
          </form>
        ) : (
          // Forgot Password Form
          <form onSubmit={handleForgotPassword}>
            <div className="form-group">
              <label htmlFor="resetEmail">Email Address</label>
              <input
                type="email"
                id="resetEmail"
                value={resetEmail}
                onChange={(e) => setResetEmail(e.target.value)}
                required
              />
            </div>
            
            <button 
              type="submit" 
              className="auth-button"
              disabled={loading}
            >
              {loading ? 'Sending...' : 'Send Reset Link'}
            </button>
            
            <div className="auth-links">
              <button 
                type="button" 
                className="text-button"
                onClick={toggleForgotPassword}
              >
                Back to Login
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
};

export default Login;