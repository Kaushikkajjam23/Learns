// src/components/DocumentUpload/DocumentUpload.jsx

import React, { useState } from 'react';
import { documentAPI } from '../../services/api';
import './DocumentUpload.css';

const DocumentUpload = () => {
  const [file, setFile] = useState(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [error, setError] = useState(null);
  const [extractedData, setExtractedData] = useState(null);
  const [success, setSuccess] = useState(null);

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0];
    if (!selectedFile) return;
    
    // Check file type
    const fileType = selectedFile.type;
    const validTypes = [
      'application/vnd.ms-excel',
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      'application/pdf',
      'application/msword',
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    ];
    
    if (!validTypes.includes(fileType)) {
      setError('Please upload a valid Excel, PDF, or Word document');
      return;
    }
    
    setFile(selectedFile);
    setError(null);
  };

  const handleUpload = async () => {
    if (!file) {
      setError('Please select a file to upload');
      return;
    }
    
    try {
      setIsUploading(true);
      setUploadProgress(0);
      setError(null);
      
      // Create form data
      const formData = new FormData();
      formData.append('file', file);
      
      // Upload file with progress tracking
      const response = await documentAPI.uploadDocument(formData, (progressEvent) => {
        const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
        setUploadProgress(progress);
      });
      
      // Set extracted data
      setExtractedData(response.data);
      setSuccess('Document uploaded and processed successfully!');
      
    } catch (err) {
      console.error('Error uploading document:', err);
      setError(`Failed to upload document: ${err.response?.data?.detail || err.message}`);
    } finally {
      setIsUploading(false);
    }
  };

  const handleCreateLearningPaths = async () => {
    if (!extractedData) {
      setError('No extracted data available');
      return;
    }
    
    try {
      setIsUploading(true);
      setError(null);
      
      // Create learning paths from extracted data
      const response = await documentAPI.createLearningPathsFromDocument(extractedData);
      
      setSuccess(`Successfully created ${response.data.created_paths.length} learning paths!`);
      setExtractedData(null);
      setFile(null);
      
      // Reload the page after 2 seconds to show the new learning paths
      setTimeout(() => {
        window.location.reload();
      }, 2000);
      
    } catch (err) {
      console.error('Error creating learning paths:', err);
      setError(`Failed to create learning paths: ${err.response?.data?.detail || err.message}`);
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="document-upload-container">
      <h2>Upload Learning Path Document</h2>
      <p className="upload-description">
        Upload a document containing topics and subtopics to generate learning paths.
        Supported formats: Excel (.xls, .xlsx), PDF (.pdf), Word (.doc, .docx)
      </p>
      
      {error && <div className="error-message">{error}</div>}
      {success && <div className="success-message">{success}</div>}
      
      <div className="upload-form">
        <div className="file-input-container">
          <input
            type="file"
            id="file-upload"
            accept=".xls,.xlsx,.pdf,.doc,.docx"
            onChange={handleFileChange}
          />
          <label htmlFor="file-upload" className="file-input-label">
            {file ? file.name : 'Choose a file'}
          </label>
        </div>
        
        {file && (
          <div className="file-info">
            <p><strong>File:</strong> {file.name}</p>
            <p><strong>Size:</strong> {(file.size / 1024 / 1024).toFixed(2)} MB</p>
          </div>
        )}
        
        <button 
          className="upload-button" 
          onClick={handleUpload} 
          disabled={!file || isUploading}
        >
          {isUploading ? 'Uploading...' : 'Upload Document'}
        </button>
        
        {isUploading && (
          <div className="progress-container">
            <div className="progress-bar">
              <div 
                className="progress-fill" 
                style={{ width: `${uploadProgress}%` }}
              ></div>
            </div>
            <p>{uploadProgress}% Uploaded</p>
          </div>
        )}
      </div>
      
      {extractedData && (
        <div className="extracted-data">
          <h3>Extracted Content</h3>
          <p>Found {extractedData.topics.length} topics in the document.</p>
          
          <div className="topics-preview">
            {extractedData.topics.slice(0, 3).map((topic, index) => (
              <div key={index} className="topic-preview">
                <h4>{topic.title}</h4>
                <p>Subtopics: {topic.subtopics.length}</p>
                <ul>
                  {topic.subtopics.slice(0, 3).map((subtopic, idx) => (
                    <li key={idx}>{subtopic}</li>
                  ))}
                  {topic.subtopics.length > 3 && <li>...</li>}
                </ul>
              </div>
            ))}
            {extractedData.topics.length > 3 && (
              <div className="topic-preview more-topics">
                <p>+ {extractedData.topics.length - 3} more topics</p>
              </div>
            )}
          </div>
          
          <button 
            className="create-paths-button"
            onClick={handleCreateLearningPaths}
            disabled={isUploading}
          >
            {isUploading ? 'Creating...' : 'Create Learning Paths'}
          </button>
        </div>
      )}
    </div>
  );
};

export default DocumentUpload;