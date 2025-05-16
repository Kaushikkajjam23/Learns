// src/components/TopicInfo.jsx
import React from 'react';

const TopicInfo = ({ info, subTopics, detailedSubtopics, onCheckboxChange }) => {
  return (
    <div className="topic-info">
      <h2>Topic Information</h2>
      <div className="overview">
        <h3>Overview</h3>
        <p>{info}</p>
      </div>
      
      <h3>Sub-topics</h3>
      <ul className="subtopics-list">
        {subTopics.map((subTopic, index) => {
          // Find the detailed info for this subtopic if available
          const detailedInfo = detailedSubtopics.find(
            (detailed) => detailed.name === subTopic.name
          );
          
          return (
            <li key={index} className="subtopic-item">
              <div className="subtopic-header">
                <label className="subtopic-checkbox">
                  <input
                    type="checkbox"
                    checked={subTopic.checked}
                    onChange={() => onCheckboxChange(index)}
                  />
                  <span className="subtopic-name">{subTopic.name}</span>
                </label>
              </div>
              
              {detailedInfo && detailedInfo.explanation && (
                <div className="subtopic-explanation">
                  <p>{detailedInfo.explanation}</p>
                </div>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
};

export default TopicInfo;