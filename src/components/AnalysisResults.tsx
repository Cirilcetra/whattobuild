import React from 'react';

interface AnalysisProps {
  analysis: {
    classification: {
      solution_requests: string[];
      pain_points: string[];
      app_ideas: string[];
      ai_solvable: string[];
    };
    summary: string;
    metadata: {
      total_posts: number;
      analyzed_posts: number;
      average_relevance: number;
      subreddit: string;
      category: string;
    };
  };
}

const AnalysisResults: React.FC<AnalysisProps> = ({ analysis }) => {
  if (!analysis) return null;

  return (
    <div className="analysis-results">
      <h2>Analysis Results</h2>
      
      <div className="summary-section">
        <h3>Summary</h3>
        <p>{analysis.summary}</p>
      </div>

      <div className="classifications">
        <h3>Classifications</h3>
        
        <div className="category">
          <h4>Solution Requests</h4>
          <ul>
            {analysis.classification.solution_requests.map((item, index) => (
              <li key={index}>{item}</li>
            ))}
          </ul>
        </div>

        <div className="category">
          <h4>Pain Points</h4>
          <ul>
            {analysis.classification.pain_points.map((item, index) => (
              <li key={index}>{item}</li>
            ))}
          </ul>
        </div>

        <div className="category">
          <h4>App Ideas</h4>
          <ul>
            {analysis.classification.app_ideas.map((item, index) => (
              <li key={index}>{item}</li>
            ))}
          </ul>
        </div>

        <div className="category">
          <h4>AI Solvable Problems</h4>
          <ul>
            {analysis.classification.ai_solvable.map((item, index) => (
              <li key={index}>{item}</li>
            ))}
          </ul>
        </div>
      </div>

      <div className="metadata">
        <h3>Metadata</h3>
        <p>Total Posts: {analysis.metadata.total_posts}</p>
        <p>Analyzed Posts: {analysis.metadata.analyzed_posts}</p>
        <p>Average Relevance: {analysis.metadata.average_relevance.toFixed(2)}</p>
        <p>Subreddit: r/{analysis.metadata.subreddit}</p>
        <p>Category: {analysis.metadata.category}</p>
      </div>
    </div>
  );
};

export default AnalysisResults; 