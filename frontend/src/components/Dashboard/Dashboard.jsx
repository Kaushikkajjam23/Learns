// src/components/Dashboard/Dashboard.jsx
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { learningPathAPI } from '../../services/api';
import './Dashboard.css';

const Dashboard = () => {
  const [learningPaths, setLearningPaths] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    const fetchLearningPaths = async () => {
      try {
        setIsLoading(true);
        const response = await learningPathAPI.getAllPaths();
        console.log("API Response:", response);
        
        // Check if response.data is an array
        const pathsData = Array.isArray(response.data) ? response.data : [];
        setLearningPaths(pathsData);
      } catch (err) {
        console.error('Error fetching learning paths:', err);
        setError('Failed to load learning paths. Please try again.');
      } finally {
        setIsLoading(false);
      }
    };

    fetchLearningPaths();
  }, []);

  if (isLoading) {
    return <div>Loading dashboard...</div>;
  }

  if (error) {
    return <div>{error}</div>;
  }

  return (
    <div>
      <h1>Learning Dashboard</h1>
      <p>Total paths: {learningPaths.length}</p>
      
      {/* Simple list of paths */}
      <ul>
        {learningPaths.map(path => (
          <li key={path.id}>{path.topic}</li>
        ))}
      </ul>
    </div>
  );
};

export default Dashboard;