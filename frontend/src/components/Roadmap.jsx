// src/components/Roadmap.jsx
import React from 'react';

const Roadmap = ({ level, completedTopics, roadmapText }) => {
  return (
    <div className="roadmap">
      <h2>Learning Roadmap</h2>
      <p><strong>Experience Level:</strong> {level}</p>
      
      {roadmapText && (
        <div className="roadmap-text">
          <pre>{roadmapText}</pre>
        </div>
      )}
      
      <div className="completed-topics">
        <h3>Completed Topics</h3>
        {completedTopics.length > 0 ? (
          <ul>
            {completedTopics.map((topic, index) => (
              <li key={index}>{topic}</li>
            ))}
          </ul>
        ) : (
          <p>No topics completed yet. Start checking off topics as you learn them!</p>
        )}
      </div>
    </div>
  );
};

export default Roadmap;