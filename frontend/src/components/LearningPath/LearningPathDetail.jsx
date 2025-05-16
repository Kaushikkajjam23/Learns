// src/components/LearningPath/LearningPathDetail.jsx
import React, { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { learningPathAPI } from '../../services/api';
import './LearningPathDetail.css';

// Import code syntax highlighter
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';

const LearningPathDetail = () => {
  const { pathId } = useParams();
  const [pathData, setPathData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [completedSubtopics, setCompletedSubtopics] = useState([]);
  const [progress, setProgress] = useState(0);
  const [activeSubtopic, setActiveSubtopic] = useState(null);
  const [showSidePanel, setShowSidePanel] = useState(false);
  const [sidePanelContent, setSidePanelContent] = useState(null);
  const [resources, setResources] = useState({});
  const [showResourceModal, setShowResourceModal] = useState(false);
  const [resourceType, setResourceType] = useState('');
  const [resourceContent, setResourceContent] = useState('');
  const [resourceTitle, setResourceTitle] = useState('');
  const [resourceUrl, setResourceUrl] = useState('');
  const [selectedLanguage, setSelectedLanguage] = useState('javascript');
  const fileInputRef = useRef(null);
  const navigate = useNavigate();

  useEffect(() => {
    const fetchLearningPath = async () => {
      try {
        setIsLoading(true);
        const response = await learningPathAPI.getPathById(pathId);
        
        console.log("Path data:", response.data);
        
        setPathData(response.data);
        setCompletedSubtopics(response.data.completed_subtopics || []);
        setProgress(response.data.progress || 0);
        
        // Fetch resources for each subtopic
        const allResources = {};
        if (response.data.subtopics_detailed) {
          for (const subtopic of response.data.subtopics_detailed) {
            try {
              const subtopicId = response.data.subtopics_detailed.indexOf(subtopic) + 1;
              const resourcesResponse = await learningPathAPI.getResources(pathId, subtopicId);
              allResources[subtopicId] = resourcesResponse.data;
            } catch (err) {
              console.error(`Error fetching resources for subtopic: ${subtopic.name}`, err);
            }
          }
        }
        
        setResources(allResources);
        
      } catch (err) {
        console.error('Error fetching learning path:', err);
        setError('Failed to load learning path. Please try again.');
      } finally {
        setIsLoading(false);
      }
    };

    fetchLearningPath();
  }, [pathId]);

  const handleSubtopicToggle = async (subtopicName) => {
    try {
      let updatedCompletedSubtopics;
      
      if (completedSubtopics.includes(subtopicName)) {
        // Remove from completed
        updatedCompletedSubtopics = completedSubtopics.filter(name => name !== subtopicName);
      } else {
        // Add to completed
        updatedCompletedSubtopics = [...completedSubtopics, subtopicName];
      }
      
      // Calculate new progress
      const newProgress = pathData.subtopics.length > 0 
        ? (updatedCompletedSubtopics.length / pathData.subtopics.length) * 100 
        : 0;
      
      // Update local state first for immediate feedback
      setCompletedSubtopics(updatedCompletedSubtopics);
      setProgress(newProgress);
      
      // Send update to server
      console.log("Sending progress update:", {
        progress: newProgress,
        completed_subtopics: updatedCompletedSubtopics
      });
      
      await learningPathAPI.updateProgress(pathId, {
        progress: newProgress,
        completed_subtopics: updatedCompletedSubtopics
      });
      
      console.log("Progress updated successfully");
    } catch (err) {
      console.error('Error updating progress:', err);
      // Show error to user
      alert("Failed to update progress. Please try again.");
      // Revert changes if update fails
      setCompletedSubtopics(completedSubtopics);
      setProgress(progress);
    }
  };

  const generateDetailedContent = async (topic, subtopicName, basicExplanation) => {
    try {
      // In a real app, you would call your API to generate content
      // For now, we'll create a more detailed version of the basic explanation
      
      // Simple enhancement of the basic explanation
      const detailedExplanation = `
${basicExplanation}

Let's explore ${subtopicName} in more detail:

${subtopicName} is a crucial concept within ${topic}. Understanding this concept helps you build a solid foundation for mastering ${topic} as a whole.

Key points to remember about ${subtopicName}:
- It forms an essential part of ${topic} fundamentals
- Mastering this concept will help you understand more advanced topics
- Practice is important for truly understanding ${subtopicName}
- Real-world applications include various scenarios in ${topic} implementation

As you continue learning, you'll discover how ${subtopicName} connects with other concepts in ${topic}.
`;

      return detailedExplanation;
    } catch (error) {
      console.error("Error generating detailed content:", error);
      return "Failed to generate detailed content.";
    }
  };

  const handleSubtopicClick = async (subtopic, index) => {
    try {
      // When a subtopic is clicked, show detailed content in the side panel
      const subtopicId = index + 1;
      setActiveSubtopic(subtopicId);
      
      // Set initial loading state
      setSidePanelContent({
        type: 'detailed',
        title: subtopic.name,
        explanation: subtopic.explanation,
        isLoading: true
      });
      setShowSidePanel(true);
      
      // Check if we already have resources for this subtopic
      let subtopicResources = resources[subtopicId] || [];
      
      // If we don't have resources yet, fetch them
      if (!subtopicResources.length) {
        try {
          const resourcesResponse = await learningPathAPI.getResources(pathId, subtopicId);
          subtopicResources = resourcesResponse.data;
          
          // Update the resources state
          setResources(prev => ({
            ...prev,
            [subtopicId]: subtopicResources
          }));
        } catch (err) {
          console.error(`Error fetching resources for subtopic: ${subtopic.name}`, err);
        }
      }
      
      // If we still don't have resources, generate them on-the-fly
      if (!subtopicResources.length) {
        // Generate a detailed explanation
        const detailedExplanation = await generateDetailedContent(pathData.topic, subtopic.name, subtopic.explanation);
        
        // Create content for the side panel with the generated explanation
        const content = {
          type: 'detailed',
          title: subtopic.name,
          explanation: subtopic.explanation,
          detailedExplanation: detailedExplanation,
          resources: subtopicResources
        };
        
        setSidePanelContent(content);
      } else {
        // We have resources, so use them
        const content = {
          type: 'detailed',
          title: subtopic.name,
          explanation: subtopic.explanation,
          resources: subtopicResources
        };
        
        setSidePanelContent(content);
      }
    } catch (error) {
      console.error("Error handling subtopic click:", error);
      setSidePanelContent({
        type: 'detailed',
        title: subtopic.name,
        explanation: subtopic.explanation,
        error: "Failed to load detailed content"
      });
    }
  };

  const handleAddResource = async (subtopicId, type) => {
    // Get the subtopic
    const subtopicIndex = subtopicId - 1;
    const subtopic = pathData.subtopics_detailed[subtopicIndex];
    
    if (!subtopic) return;
    
    // Set the active subtopic for the side panel
    setActiveSubtopic(subtopicId);
    setResourceType(type);
    setResourceContent('');
    setResourceTitle('');
    setResourceUrl('');
    setShowResourceModal(true);
  };

  const handleResourceSubmit = async (e) => {
    e.preventDefault();
    
    try {
      let finalContent = resourceContent;
      
      // If it's an image upload, handle the file
      if (resourceType === 'image' && fileInputRef.current.files.length > 0) {
        const file = fileInputRef.current.files[0];
        const formData = new FormData();
        formData.append('file', file);
        
        const response = await learningPathAPI.uploadFile(formData);
        finalContent = response.data.url;
      }
      
      await learningPathAPI.addResource(pathId, activeSubtopic, {
        type: resourceType,
        content: finalContent,
        title: resourceTitle,
        url: resourceUrl,
        language: selectedLanguage
      });
      
      // Refresh the learning path data
      const response = await learningPathAPI.getPathById(pathId);
      setPathData(response.data);
      
      // Update resources for the active subtopic
      const resourcesResponse = await learningPathAPI.getResources(pathId, activeSubtopic);
      setResources(prev => ({
        ...prev,
        [activeSubtopic]: resourcesResponse.data
      }));
      
      // Close the modal
      setShowResourceModal(false);
    } catch (err) {
      console.error('Error adding resource:', err);
      alert('Failed to add resource. Please try again.');
    }
  };

  const closeSidePanel = () => {
    setShowSidePanel(false);
    setSidePanelContent(null);
  };

  if (isLoading) {
    return <div className="loading">Loading learning path...</div>;
  }

  if (error || !pathData) {
    return <div className="error-message">{error || 'Failed to load learning path'}</div>;
  }

  return (
    <div className="learning-path-detail">
      <div className="path-header">
        <button className="back-button" onClick={() => navigate('/dashboard')}>
          ← Back to Dashboard
        </button>
        <h1>{pathData.topic}</h1>
        <div className="path-meta">
          <span className="level-badge">{pathData.level}</span>
          <span className="estimated-time">
            Estimated time: {pathData.estimated_hours} hours
          </span>
        </div>
      </div>

      <div className="progress-section">
        <h2>Your Progress</h2>
        <div className="progress-bar-container">
          <div className="progress-stats">
            <span>{progress.toFixed(0)}% Complete</span>
            <span>
              {completedSubtopics.length}/{pathData.subtopics.length} Topics
            </span>
          </div>
          <progress value={progress} max="100"></progress>
        </div>
      </div>

      <div className="path-content">
        <div className="overview-section">
          <h2>Overview</h2>
          <div className="content-box">
            <p>{pathData.overview}</p>
          </div>
        </div>

        <div className="subtopics-section">
          <h2>Learning Topics</h2>
          <div className="subtopics-list">
            {pathData.subtopics_detailed.map((subtopic, index) => {
              const isCompleted = completedSubtopics.includes(subtopic.name);
              const subtopicId = index + 1;
              
              return (
                <div 
                  key={index} 
                  className={`subtopic-card ${isCompleted ? 'completed' : ''} ${activeSubtopic === subtopicId && showSidePanel ? 'active' : ''}`}
                >
                  <div className="subtopic-header">
                    <label className="checkbox-container">
                      <input
                        type="checkbox"
                        checked={isCompleted}
                        onChange={() => handleSubtopicToggle(subtopic.name)}
                      />
                      <span className="checkmark"></span>
                    </label>
                    <h3 
                      onClick={() => handleSubtopicClick(subtopic, index)}
                      className="clickable-heading"
                    >
                      {subtopic.name}
                    </h3>
                  </div>
                  
                  <div className="subtopic-content">
                    <p>{subtopic.explanation}</p>
                    
                    <div className="resource-buttons">
                      <button 
                        className="resource-button"
                        onClick={() => handleAddResource(subtopicId, 'image')}
                        title="View Images"
                      >
                        <span className="icon">🖼️</span>
                      </button>
                      <button 
                        className="resource-button"
                        onClick={() => handleAddResource(subtopicId, 'code')}
                        title="View Code Examples"
                      >
                        <span className="icon">💻</span>
                      </button>
                      <button 
                        className="resource-button"
                        onClick={() => handleAddResource(subtopicId, 'reference')}
                        title="View References"
                      >
                        <span className="icon">📚</span>
                      </button>
                      <button 
                        className="resource-button"
                        onClick={() => handleAddResource(subtopicId, 'video')}
                        title="View Videos"
                      >
                        <span className="icon">🎬</span>
                      </button>
                    </div>
                    
                    {/* Display resources for this subtopic */}
                    <div className="resources-container">
                      {resources[subtopicId] && resources[subtopicId].length > 0 && 
                        resources[subtopicId].map((resource, idx) => (
                          <div key={idx} className={`resource-item ${resource.type}`}>
                            {resource.title && <h4>{resource.title}</h4>}
                            
                            {resource.type === 'image' && resource.content && (
                              <img src={resource.content} alt={resource.title || 'Resource image'} />
                            )}
                            
                            {resource.type === 'code' && (
                              <SyntaxHighlighter language={resource.language || 'javascript'} style={vscDarkPlus}>
                                {resource.content}
                              </SyntaxHighlighter>
                            )}
                            
                            {resource.type === 'reference' && (
                              <div className="reference">
                                <p>{resource.content}</p>
                                {resource.url && (
                                  <a href={resource.url} target="_blank" rel="noopener noreferrer">
                                    Visit Reference
                                  </a>
                                )}
                              </div>
                            )}
                            
                            {resource.type === 'video' && (
                              <div className="video-container">
                                {resource.url && resource.url.includes('youtube') ? (
                                  <iframe
                                    width="100%"
                                    height="215"
                                    src={resource.url.replace('watch?v=', 'embed/').split('&')[0]}
                                    title={resource.title || 'Video'}
                                    frameBorder="0"
                                    allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                                    allowFullScreen
                                  ></iframe>
                                ) : (
                                  <a href={resource.url} target="_blank" rel="noopener noreferrer">
                                    Watch Video
                                  </a>
                                )}
                              </div>
                            )}
                          </div>
                        ))
                      }
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        <div className="roadmap-section">
          <h2>Learning Roadmap</h2>
          <div className="content-box roadmap-box">
            <pre>{pathData.roadmap}</pre>
          </div>
        </div>
      </div>
      
      {/* Side Panel for Detailed Content */}
      {showSidePanel && sidePanelContent && (
        <div className="side-panel">
          <div className="side-panel-header">
            <h3>{sidePanelContent.title || 'Details'}</h3>
            <button className="close-button" onClick={closeSidePanel}>×</button>
          </div>
          
          <div className="side-panel-content">
            {sidePanelContent.isLoading ? (
              <div className="loading">Loading content...</div>
            ) : sidePanelContent.error ? (
              <div className="error-message">{sidePanelContent.error}</div>
            ) : (
              <>
                {sidePanelContent.type === 'detailed' && (
                  <div className="detailed-content">
                    <h4>Basic Explanation</h4>
                    <p className="basic-explanation">{sidePanelContent.explanation}</p>
                    
                    {sidePanelContent.detailedExplanation && (
                      <>
                        <h4>Detailed Explanation</h4>
                        <div className="detailed-explanation">
                          {sidePanelContent.detailedExplanation.split('\n\n').map((paragraph, idx) => {
                            // Skip empty paragraphs
                            if (!paragraph.trim()) return null;
                            
                            // Format headings
                            if (paragraph.startsWith('###') || paragraph.startsWith('##')) {
                              const headingText = paragraph.replace(/^#+\s*/, '').replace(/\*\*/g, '');
                              return <h5 key={idx} className="content-heading">{headingText}</h5>;
                            }
                            
                            // Format lists
                            if (paragraph.includes('\n-') || paragraph.includes('\n1.')) {
                              const listItems = paragraph.split('\n').filter(item => item.trim());
                              const isOrdered = listItems[0].match(/^\d+\./);
                              
                              if (isOrdered) {
                                return (
                                  <ol key={idx} className="content-list">
                                    {listItems.map((item, i) => {
                                      const cleanItem = item.replace(/^\d+\.\s*/, '');
                                      return <li key={i}>{cleanItem}</li>;
                                    })}
                                  </ol>
                                );
                              } else {
                                return (
                                  <ul key={idx} className="content-list">
                                    {listItems.map((item, i) => {
                                      const cleanItem = item.replace(/^-\s*/, '');
                                      return <li key={i}>{cleanItem}</li>;
                                    })}
                                  </ul>
                                );
                              }
                            }
                            
                            // Format code blocks
                            if (paragraph.includes('```')) {
                              const parts = paragraph.split('```');
                              return (
                                <div key={idx}>
                                  {parts.map((part, i) => {
                                    if (i % 2 === 0) {
                                      return part ? <p key={`text-${i}`}>{part}</p> : null;
                                    } else {
                                      const language = part.split('\n')[0];
                                      const code = part.substring(language.length + 1);
                                      return (
                                        <SyntaxHighlighter 
                                          key={`code-${i}`} 
                                          language={language || 'javascript'} 
                                          style={vscDarkPlus}
                                        >
                                          {code}
                                        </SyntaxHighlighter>
                                      );
                                    }
                                  })}
                                </div>
                              );
                            }
                            
                            // Handle bold and italic text
                            const formattedText = paragraph
                              .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
                              .replace(/\*([^*]+)\*/g, '<em>$1</em>')
                              .replace(/---/g, '<hr />');
                            
                            return <p key={idx} dangerouslySetInnerHTML={{ __html: formattedText }} />;
                          })}
                        </div>
                      </>
                    )}
                    
                    {sidePanelContent.resources && sidePanelContent.resources.length > 0 && (
                      <div className="resources-list">
                        <h4>Resources</h4>
                        {sidePanelContent.resources.map((resource, idx) => (
                          <div key={idx} className={`resource-item ${resource.type}`}>
                            {resource.title && <h5>{resource.title}</h5>}
                            
                            {resource.type === 'image' && resource.url && (
                              <img src={resource.url} alt={resource.content || 'Resource image'} />
                            )}
                            
                            {resource.type === 'code' && (
                              <SyntaxHighlighter language={resource.language || 'javascript'} style={vscDarkPlus}>
                                {resource.content}
                              </SyntaxHighlighter>
                            )}
                            
                            {resource.type === 'reference' && (
                              <div className="reference">
                                <p>{resource.content}</p>
                                {resource.url && (
                                  <a href={resource.url} target="_blank" rel="noopener noreferrer">
                                    Visit Reference
                                  </a>
                                )}
                              </div>
                            )}
                            
                            {resource.type === 'video' && (
                              <div className="video-container">
                                {resource.url && resource.url.includes('youtube.com') ? (
                                  <iframe
                                    width="100%"
                                    height="215"
                                    src={resource.url.replace('watch?v=', 'embed/').split('&')[0]}
                                    title={resource.title || 'Video'}
                                    frameBorder="0"
                                    allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                                    allowFullScreen
                                  ></iframe>
                                ) : (
                                  <a href={resource.url} target="_blank" rel="noopener noreferrer">
                                    Watch Video
                                  </a>
                                )}
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
                
                {sidePanelContent.type === 'image' && (
                  <div className="image-gallery">
                    {sidePanelContent.resources.map((image, idx) => (
                      <div key={idx} className="gallery-item">
                        <img src={image.url} alt={image.description} />
                        <p>{image.description}</p>
                      </div>
                    ))}
                  </div>
                )}
                
                {sidePanelContent.type === 'code' && (
                  <div className="code-examples">
                    {sidePanelContent.resources.map((code, idx) => (
                      <div key={idx} className="code-example">
                        <SyntaxHighlighter language={code.language} style={vscDarkPlus}>
                          {code.code}
                        </SyntaxHighlighter>
                      </div>
                    ))}
                  </div>
                )}
                
                {sidePanelContent.type === 'reference' && (
                  <div className="references">
                    {sidePanelContent.resources.map((ref, idx) => (
                      <div key={idx} className="reference-item">
                        <h4>{ref.title}</h4>
                        <p>{ref.description}</p>
                        <a href={ref.url} target="_blank" rel="noopener noreferrer">
                          Visit Reference
                        </a>
                      </div>
                    ))}
                  </div>
                )}
                
                {sidePanelContent.type === 'video' && (
                  <div className="video-gallery">
                    {sidePanelContent.resources.map((video, idx) => (
                      <div key={idx} className="video-item">
                        <h4>{video.title}</h4>
                        <p>{video.description}</p>
                        {video.url && video.url.includes('youtube.com') ? (
                          <iframe
                            width="100%"
                            height="215"
                            src={video.url.replace('watch?v=', 'embed/').split('&')[0]}
                            title={video.title}
                            frameBorder="0"
                            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                            allowFullScreen
                          ></iframe>
                        ) : (
                          <a href={video.url} target="_blank" rel="noopener noreferrer" className="video-link">
                            Watch Video
                          </a>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      )}

      {/* Resource Modal */}
      {showResourceModal && (
        <div className="modal-overlay">
          <div className="modal-content">
            <div className="modal-header">
              <h3>Add {resourceType.charAt(0).toUpperCase() + resourceType.slice(1)}</h3>
              <button className="close-button" onClick={() => setShowResourceModal(false)}>×</button>
            </div>
            
            <form onSubmit={handleResourceSubmit}>
              <div className="form-group">
                <label htmlFor="resourceTitle">Title (Optional)</label>
                <input
                  type="text"
                  id="resourceTitle"
                  value={resourceTitle}
                  onChange={(e) => setResourceTitle(e.target.value)}
                  placeholder="Enter a title for this resource"
                />
              </div>
              
              {resourceType === 'image' ? (
                <div className="form-group">
                  <label htmlFor="resourceFile">Upload Image</label>
                  <input
                    type="file"
                    id="resourceFile"
                    ref={fileInputRef}
                    accept="image/*"
                  />
                </div>
              ) : resourceType === 'code' ? (
                <>
                  <div className="form-group">
                    <label htmlFor="codeLanguage">Language</label>
                    <select
                      id="codeLanguage"
                      value={selectedLanguage}
                      onChange={(e) => setSelectedLanguage(e.target.value)}
                    >
                      <option value="javascript">JavaScript</option>
                      <option value="python">Python</option>
                      <option value="java">Java</option>
                      <option value="csharp">C#</option>
                      <option value="cpp">C++</option>
                      <option value="php">PHP</option>
                      <option value="ruby">Ruby</option>
                      <option value="swift">Swift</option>
                      <option value="go">Go</option>
                      <option value="typescript">TypeScript</option>
                      <option value="sql">SQL</option>
                      <option value="html">HTML</option>
                      <option value="css">CSS</option>
                    </select>
                  </div>
                  <div className="form-group">
                    <label htmlFor="resourceContent">Code</label>
                    <textarea
                      id="resourceContent"
                      value={resourceContent}
                      onChange={(e) => setResourceContent(e.target.value)}
                      placeholder="Paste your code here"
                      rows={10}
                      required
                    ></textarea>
                  </div>
                </>
              ) : (
                <div className="form-group">
                  <label htmlFor="resourceContent">Content</label>
                  <textarea
                    id="resourceContent"
                    value={resourceContent}
                    onChange={(e) => setResourceContent(e.target.value)}
                    placeholder={`Enter ${resourceType} content`}
                    rows={5}
                    required
                  ></textarea>
                </div>
              )}
              
              {(resourceType === 'reference' || resourceType === 'video') && (
                <div className="form-group">
                  <label htmlFor="resourceUrl">URL (Optional)</label>
                  <input
                    type="url"
                    id="resourceUrl"
                    value={resourceUrl}
                    onChange={(e) => setResourceUrl(e.target.value)}
                    placeholder="Enter a URL"
                  />
                </div>
              )}
              
              <div className="form-actions">
                <button type="button" onClick={() => setShowResourceModal(false)}>Cancel</button>
                <button type="submit">Add {resourceType}</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default LearningPathDetail;