// src/components/DocumentUpload/AssignLearningPathsPage.jsx
import React, { useState, useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { documentAPI, userAPI } from '../../services/api';


const AssignLearningPathsPage = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const [createdPaths, setCreatedPaths] = useState([]);
  const [employees, setEmployees] = useState([]);
  const [assignments, setAssignments] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [successMessage, setSuccessMessage] = useState(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setIsLoading(true);
        
        // Get created paths from location state or fetch from API
        let paths = [];
        if (location.state?.createdPaths) {
          paths = location.state.createdPaths;
        } else {
          // Fetch recently created paths
          const pathsResponse = await documentAPI.getRecentlyCreatedPaths();
          paths = pathsResponse.data;
        }
        
        setCreatedPaths(paths);
        
        // Fetch employees
        const employeesResponse = await userAPI.getAllEmployees();
        setEmployees(employeesResponse.data);
        
        // Initialize assignments
        const initialAssignments = paths.map(path => ({
          pathId: path.id,
          employeeIds: [],
          deadline: getDefaultDeadline(),
          priority: 'Medium'
        }));
        
        setAssignments(initialAssignments);
        
      } catch (err) {
        console.error('Error fetching data:', err);
        setError(`Failed to load data: ${err.response?.data?.detail || err.message}`);
      } finally {
        setIsLoading(false);
      }
    };
    
    fetchData();
  }, [location.state]);

  const getDefaultDeadline = () => {
    const date = new Date();
    date.setDate(date.getDate() + 30); // Default: 30 days from now
    return date.toISOString().split('T')[0]; // Format as YYYY-MM-DD
  };

  const handleEmployeeSelection = (pathIndex, employeeId) => {
    const updatedAssignments = [...assignments];
    const currentAssignment = updatedAssignments[pathIndex];
    
    // Toggle employee selection
    if (currentAssignment.employeeIds.includes(employeeId)) {
      currentAssignment.employeeIds = currentAssignment.employeeIds.filter(id => id !== employeeId);
    } else {
      currentAssignment.employeeIds.push(employeeId);
    }
    
    setAssignments(updatedAssignments);
  };

  const handleSelectAll = (pathIndex) => {
    const updatedAssignments = [...assignments];
    updatedAssignments[pathIndex].employeeIds = employees.map(emp => emp.id);
    setAssignments(updatedAssignments);
  };

  const handleClearAll = (pathIndex) => {
    const updatedAssignments = [...assignments];
    updatedAssignments[pathIndex].employeeIds = [];
    setAssignments(updatedAssignments);
  };

  const handleDateChange = (pathIndex, date) => {
    const updatedAssignments = [...assignments];
    updatedAssignments[pathIndex].deadline = date;
    setAssignments(updatedAssignments);
  };

  const handlePriorityChange = (pathIndex, priority) => {
    const updatedAssignments = [...assignments];
    updatedAssignments[pathIndex].priority = priority;
    setAssignments(updatedAssignments);
  };

  const handleSubmit = async () => {
    try {
      setIsSubmitting(true);
      setError(null);
      
      // Filter out assignments with no employees
      const validAssignments = assignments.filter(assignment => assignment.employeeIds.length > 0);
      
      if (validAssignments.length === 0) {
        setError('Please assign at least one learning path to an employee');
        setIsSubmitting(false);
        return;
      }
      
      // Submit assignments
      await documentAPI.assignLearningPaths(validAssignments);
      
      setSuccessMessage('Learning paths assigned successfully!');
      
      // Clear form after 2 seconds
      setTimeout(() => {
        navigate('/dashboard');
      }, 2000);
      
    } catch (err) {
      console.error('Error assigning learning paths:', err);
      setError(`Failed to assign learning paths: ${err.response?.data?.detail || err.message}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  if (isLoading) {
    return <div className="loading">Loading data...</div>;
  }

  return (
    <div className="assign-learning-paths-page">
      <h1>Assign Learning Paths</h1>
      
      {error && <div className="error-message">{error}</div>}
      {successMessage && <div className="success-message">{successMessage}</div>}
      
      <div className="assignments-container">
        {createdPaths.map((path, pathIndex) => (
          <div key={path.id} className="assignment-card">
            <div className="path-info">
              <h2>{path.topic}</h2>
              <div className="path-meta">
                <span className="level-badge">{path.level}</span>
                <span>{path.subtopics.length} subtopics</span>
                <span>~{path.estimated_hours} hours</span>
              </div>
              <p className="path-description">{path.overview.substring(0, 150)}...</p>
            </div>
            
            <div className="assignment-details">
              <div className="form-group">
                <label>Deadline:</label>
                <input
                  type="date"
                  value={assignments[pathIndex].deadline}
                  onChange={(e) => handleDateChange(pathIndex, e.target.value)}
                  min={new Date().toISOString().split('T')[0]}
                />
              </div>
              
              <div className="form-group">
                <label>Priority:</label>
                <select
                  value={assignments[pathIndex].priority}
                  onChange={(e) => handlePriorityChange(pathIndex, e.target.value)}
                >
                  <option value="Low">Low</option>
                  <option value="Medium">Medium</option>
                  <option value="High">High</option>
                  <option value="Critical">Critical</option>
                </select>
              </div>
            </div>
            
            <div className="employee-selection">
              <div className="selection-header">
                <h3>Assign to Employees</h3>
                <div className="selection-actions">
                  <button onClick={() => handleSelectAll(pathIndex)}>Select All</button>
                  <button onClick={() => handleClearAll(pathIndex)}>Clear</button>
                </div>
              </div>
              
              <div className="employees-list">
                {employees.map(employee => (
                  <label key={employee.id} className="employee-checkbox">
                    <input
                      type="checkbox"
                      checked={assignments[pathIndex].employeeIds.includes(employee.id)}
                      onChange={() => handleEmployeeSelection(pathIndex, employee.id)}
                    />
                    <span className="employee-name">{employee.name}</span>
                    <span className="employee-email">{employee.email}</span>
                  </label>
                ))}
              </div>
              
              <div className="selected-count">
                {assignments[pathIndex].employeeIds.length} employees selected
              </div>
            </div>
          </div>
        ))}
      </div>
      
      <div className="action-buttons">
        <button 
          className="cancel-button"
          onClick={() => navigate('/document-review')}
        >
          Back to Review
        </button>
        <button 
          className="submit-button"
          onClick={handleSubmit}
          disabled={isSubmitting}
        >
          {isSubmitting ? 'Assigning...' : 'Assign Learning Paths'}
        </button>
      </div>
    </div>
  );
};

export default AssignLearningPathsPage;