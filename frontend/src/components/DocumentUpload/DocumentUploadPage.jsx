// src/components/DocumentUpload/DocumentUploadPage.jsx
import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { documentAPI } from '../../services/api';
import './DocumentUpload.css';

const DocumentUploadPage = () => {
  const [file, setFile] = useState(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [error, setError] = useState(null);
  const [extractedData, setExtractedData] = useState(null);
  const navigate = useNavigate();

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
      
    } catch (err) {
      console.error('Error uploading document:', err);
      setError(`Failed to upload document: ${err.response?.data?.detail || err.message}`);
    } finally {
      setIsUploading(false);
    }
  };

  const handleReviewData = () => {
    // Store extracted data in session storage for the review page
    sessionStorage.setItem('extractedData', JSON.stringify(extractedData));
    navigate('/document-review');
  };

  return (
    <div className="document-upload-page">
      <h1>Upload Learning Path Document</h1>
      <div className="upload-container">
        <div className="upload-instructions">
          <h2>Instructions</h2>
          <p>Upload a document containing topics and subtopics for learning paths:</p>
          <ul>
            <li>Excel (.xls, .xlsx): Use columns for topics and subtopics</li>
            <li>PDF (.pdf): Ensure the document has a clear structure</li>
            <li>Word (.doc, .docx): Use headings for topics and bullet points for subtopics</li>
          </ul>
          <div className="template-links">
            <h3>Download Templates</h3>
            <a href="/templates/learning_path_template.xlsx" download>Excel Template</a>
            <a href="/templates/learning_path_template.docx" download>Word Template</a>
            <a href="/templates/learning_path_template.pdf" download>PDF Template</a>
          </div>
        </div>
        
        <div className="upload-form">
          <div className="file-drop-area">
            <input
              type="file"
              id="file-upload"
              accept=".xls,.xlsx,.pdf,.doc,.docx"
              onChange={handleFileChange}
            />
            <label htmlFor="file-upload" className="file-label">
              {file ? file.name : 'Choose a file or drag it here'}
            </label>
          </div>
          
          {file && (
            <div className="file-info">
              <p><strong>Selected file:</strong> {file.name}</p>
              <p><strong>File size:</strong> {(file.size / 1024 / 1024).toFixed(2)} MB</p>
              <p><strong>File type:</strong> {file.type}</p>
            </div>
          )}
          
          {error && <div className="error-message">{error}</div>}
          
          <button 
            className="upload-button" 
            onClick={handleUpload} 
            disabled={!file || isUploading}
          >
            {isUploading ? 'Uploading...' : 'Upload Document'}
          </button>
          
          {isUploading && (
            <div className="upload-progress">
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
      </div>
      
      {extractedData && (
        <div className="extracted-data-preview">
          <h2>Extracted Content Preview</h2>
          <p>We've extracted {extractedData.topics.length} topics from your document.</p>
          
          <div className="preview-box">
            <h3>Topics Overview:</h3>
            <ul>
              {extractedData.topics.slice(0, 5).map((topic, index) => (
                <li key={index}>{topic.title} ({topic.subtopics.length} subtopics)</li>
              ))}
              {extractedData.topics.length > 5 && <li>...and {extractedData.topics.length - 5} more</li>}
            </ul>
          </div>
          
          <button 
            className="review-button"
            onClick={handleReviewData}
          >
            Review & Edit Content
          </button>
        </div>
      )}
    </div>
  );
};

export default DocumentUploadPage;