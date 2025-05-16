// src/components/DocumentUpload/DocumentReviewPage.jsx
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { documentAPI } from '../../services/api';


const DocumentReviewPage = () => {
  const [extractedData, setExtractedData] = useState(null);
  const [editedData, setEditedData] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    // Get extracted data from session storage
    const storedData = sessionStorage.getItem('extractedData');
    if (!storedData) {
      navigate('/document-upload');
      return;
    }
    
    const parsedData = JSON.parse(storedData);
    setExtractedData(parsedData);
    setEditedData(JSON.parse(JSON.stringify(parsedData))); // Deep copy
  }, [navigate]);

  const handleTopicChange = (index, field, value) => {
    const updatedData = { ...editedData };
    updatedData.topics[index][field] = value;
    setEditedData(updatedData);
  };

  const handleSubtopicChange = (topicIndex, subtopicIndex, value) => {
    const updatedData = { ...editedData };
    updatedData.topics[topicIndex].subtopics[subtopicIndex] = value;
    setEditedData(updatedData);
  };

  const addSubtopic = (topicIndex) => {
    const updatedData = { ...editedData };
    updatedData.topics[topicIndex].subtopics.push('New Subtopic');
    setEditedData(updatedData);
  };

  const removeSubtopic = (topicIndex, subtopicIndex) => {
    const updatedData = { ...editedData };
    updatedData.topics[topicIndex].subtopics.splice(subtopicIndex, 1);
    setEditedData(updatedData);
  };

  const addTopic = () => {
    const updatedData = { ...editedData };
    updatedData.topics.push({
      title: 'New Topic',
      description: 'Enter topic description',
      level: 'Intermediate',
      subtopics: ['New Subtopic']
    });
    setEditedData(updatedData);
  };

  const removeTopic = (topicIndex) => {
    const updatedData = { ...editedData };
    updatedData.topics.splice(topicIndex, 1);
    setEditedData(updatedData);
  };

  const handleSubmit = async () => {
    try {
      setIsSubmitting(true);
      setError(null);
      
      // Submit the edited data to create learning paths
      const response = await documentAPI.createLearningPathsFromDocument(editedData);
      
      // Clear session storage
      sessionStorage.removeItem('extractedData');
      
      // Navigate to assignment page with the created learning paths
      navigate('/assign-learning-paths', { 
        state: { createdPaths: response.data.created_paths }
      });
      
    } catch (err) {
      console.error('Error creating learning paths:', err);
      setError(`Failed to create learning paths: ${err.response?.data?.detail || err.message}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  if (!editedData) {
    return <div className="loading">Loading extracted data...</div>;
  }

  return (
    <div className="document-review-page">
      <h1>Review Extracted Content</h1>
      <p className="review-instructions">
        Review and edit the extracted topics and subtopics before creating learning paths.
      </p>
      
      {error && <div className="error-message">{error}</div>}
      
      <div className="topics-container">
        {editedData.topics.map((topic, topicIndex) => (
          <div key={topicIndex} className="topic-card">
            <div className="topic-header">
              <input
                type="text"
                value={topic.title}
                onChange={(e) => handleTopicChange(topicIndex, 'title', e.target.value)}
                className="topic-title-input"
              />
              <button 
                className="remove-button"
                onClick={() => removeTopic(topicIndex)}
                title="Remove Topic"
              >
                ×
              </button>
            </div>
            
            <div className="topic-details">
              <div className="form-group">
                <label>Description:</label>
                <textarea
                  value={topic.description}
                  onChange={(e) => handleTopicChange(topicIndex, 'description', e.target.value)}
                  rows="3"
                />
              </div>
              
              <div className="form-group">
                <label>Level:</label>
                <select
                  value={topic.level}
                  onChange={(e) => handleTopicChange(topicIndex, 'level', e.target.value)}
                >
                  <option value="Beginner">Beginner</option>
                  <option value="Intermediate">Intermediate</option>
                  <option value="Advanced">Advanced</option>
                  <option value="Expert">Expert</option>
                </select>
              </div>
            </div>
            
            <div className="subtopics-section">
              <h3>Subtopics</h3>
              <ul className="subtopics-list">
                {topic.subtopics.map((subtopic, subtopicIndex) => (
                  <li key={subtopicIndex} className="subtopic-item">
                    <input
                      type="text"
                      value={subtopic}
                      onChange={(e) => handleSubtopicChange(topicIndex, subtopicIndex, e.target.value)}
                    />
                    <button 
                      className="remove-button small"
                      onClick={() => removeSubtopic(topicIndex, subtopicIndex)}
                      title="Remove Subtopic"
                    >
                      ×
                    </button>
                  </li>
                ))}
              </ul>
              
              <button 
                className="add-button"
                onClick={() => addSubtopic(topicIndex)}
              >
                + Add Subtopic
              </button>
            </div>
          </div>
        ))}
        
        <button 
          className="add-topic-button"
          onClick={addTopic}
        >
          + Add New Topic
        </button>
      </div>
      
      <div className="action-buttons">
        <button 
          className="cancel-button"
          onClick={() => navigate('/document-upload')}
        >
          Back to Upload
        </button>
        <button 
          className="submit-button"
          onClick={handleSubmit}
          disabled={isSubmitting}
        >
          {isSubmitting ? 'Creating Learning Paths...' : 'Create Learning Paths'}
        </button>
      </div>
    </div>
  );
};

export default DocumentReviewPage;