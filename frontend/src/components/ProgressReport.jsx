// src/components/ProgressReport.jsx
import React from 'react';

const ProgressReport = ({ progress }) => {
  return (
    <div>
      <h2>Progress Report</h2>
      <progress value={progress} max="100" />
      <p>{progress}% completed</p>
    </div>
  );
};

export default ProgressReport;