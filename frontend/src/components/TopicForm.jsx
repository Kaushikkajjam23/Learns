// src/components/TopicForm.jsx
import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { learningPathAPI } from '../services/api';
import './TopicForm.css';

const TopicForm = () => {
  const [topic, setTopic] = useState('');
  const [level, setLevel] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [showOptions, setShowOptions] = useState(false);
  const [includeImages, setIncludeImages] = useState(false);
  const [includeCode, setIncludeCode] = useState(false);
  const [includeReferences, setIncludeReferences] = useState(false);
  const [includeVideos, setIncludeVideos] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);
    
    try {
      const response = await learningPathAPI.createPath({ 
        topic, 
        level,
        preferences: {
          includeImages,
          includeCode,
          includeReferences,
          includeVideos
        }
      });
      
      console.log('Response received:', response.data);
      
      // Check if the response has the expected format
      if (response.data.id) {
        // Navigate to the newly created learning path
        navigate(`/learning-path/${response.data.id}`);
      } else {
        setError('Received unexpected response format from server');
        console.error('Unexpected response format:', response.data);
      }
    } catch (error) {
      setError(`Error: ${error.response?.data?.detail || error.message}`);
      console.error('Error:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleTopicChange = (e) => {
    setTopic(e.target.value);
    // Show options when user starts typing
    if (e.target.value.length > 0 && !showOptions) {
      setShowOptions(true);
    } else if (e.target.value.length === 0) {
      setShowOptions(false);
    }
  };

  return (
    <div className="topic-form-container">
      <h1>Create a New Learning Path</h1>
      <div className="form-card">
        {error && <div className="error-message">{error}</div>}
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="topic">What do you want to learn?</label>
            <div className="input-with-options">
              <input
                id="topic"
                type="text"
                placeholder="Enter a topic (e.g., Machine Learning, React, Data Structures)"
                value={topic}
                onChange={handleTopicChange}
                required
              />
              {topic.length > 0 && (
                <div className="input-options">
                  <button 
                    type="button" 
                    className={`option-button ${includeImages ? 'active' : ''}`}
                    onClick={() => setIncludeImages(!includeImages)}
                    title="Include images"
                  >
                    🖼️
                  </button>
                  <button 
                    type="button" 
                    className={`option-button ${includeCode ? 'active' : ''}`}
                    onClick={() => setIncludeCode(!includeCode)}
                    title="Include code examples"
                  >
                    💻
                  </button>
                  <button 
                    type="button" 
                    className={`option-button ${includeReferences ? 'active' : ''}`}
                    onClick={() => setIncludeReferences(!includeReferences)}
                    title="Include references"
                  >
                    📚
                  </button>
                  <button 
                    type="button" 
                    className={`option-button ${includeVideos ? 'active' : ''}`}
                    onClick={() => setIncludeVideos(!includeVideos)}
                    title="Include videos"
                  >
                    🎬
                  </button>
                </div>
              )}
            </div>
          </div>
          
          <div className="form-group">
            <label htmlFor="level">Your Experience Level</label>
            <select 
              id="level"
              value={level} 
              onChange={(e) => setLevel(e.target.value)}
              required
            >
              <option value="">Select your level</option>
              <option value="Junior">Beginner</option>
              <option value="Intermediate">Intermediate</option>
              <option value="Senior">Advanced</option>
              <option value="Lead">Expert</option>
            </select>
          </div>
          
          {showOptions && (
            <div className="preferences-section">
              <h3>Content Preferences</h3>
              <div className="preferences-grid">
                <div className={`preference-item ${includeImages ? 'active' : ''}`}>
                  <input
                    type="checkbox"
                    id="includeImages"
                    checked={includeImages}
                    onChange={() => setIncludeImages(!includeImages)}
                  />
                  <label htmlFor="includeImages">
                    <span className="preference-icon">🖼️</span>
                    <span className="preference-text">Include Images</span>
                  </label>
                </div>
                
                <div className={`preference-item ${includeCode ? 'active' : ''}`}>
                  <input
                    type="checkbox"
                    id="includeCode"
                    checked={includeCode}
                    onChange={() => setIncludeCode(!includeCode)}
                  />
                  <label htmlFor="includeCode">
                    <span className="preference-icon">💻</span>
                    <span className="preference-text">Include Code Examples</span>
                  </label>
                </div>
                
                <div className={`preference-item ${includeReferences ? 'active' : ''}`}>
                  <input
                    type="checkbox"
                    id="includeReferences"
                    checked={includeReferences}
                    onChange={() => setIncludeReferences(!includeReferences)}
                  />
                  <label htmlFor="includeReferences">
                    <span className="preference-icon">📚</span>
                    <span className="preference-text">Include References</span>
                  </label>
                </div>
                
                <div className={`preference-item ${includeVideos ? 'active' : ''}`}>
                  <input
                    type="checkbox"
                    id="includeVideos"
                    checked={includeVideos}
                    onChange={() => setIncludeVideos(!includeVideos)}
                  />
                  <label htmlFor="includeVideos">
                    <span className="preference-icon">🎬</span>
                    <span className="preference-text">Include Videos</span>
                  </label>
                </div>
              </div>
            </div>
          )}
          
          <button type="submit" className="submit-button" disabled={isLoading}>
            {isLoading ? 'Creating your learning path...' : 'Create Learning Path'}
          </button>
        </form>
      </div>
    </div>
  );
};

export default TopicForm;