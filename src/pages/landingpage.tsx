import React, { useState } from "react";
import "./landingpage.css"; // Import the CSS file with correct name
import { analyzeRedditPosts, AnalysisResult } from "../openai/openai";

interface Keyword {
  text: string;
  relevance: number;
}

interface SubredditSuggestion {
  name: string;
  description: string;
  subscribers: number;
}

const LandingPage = (): JSX.Element => {
  const [ideaDescription, setIdeaDescription] = useState("");
  const [keywords, setKeywords] = useState<Keyword[]>([]);
  const [subreddits, setSubreddits] = useState<SubredditSuggestion[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const generateKeywords = async () => {
    if (!ideaDescription.trim()) return;
    
    setLoading(true);
    setError("");
    
    try {
      const response = await fetch('http://localhost:8000/generate_keywords', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ description: ideaDescription }),
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      setKeywords(data.keywords);
      
      // After getting keywords, fetch subreddit suggestions
      if (data.keywords.length > 0) {
        await findSubreddits(data.keywords);
      }
    } catch (err) {
      console.error("Error:", err);
      setError(`Failed to generate keywords: ${err instanceof Error ? err.message : 'Unknown error'}`);
    } finally {
      setLoading(false);
    }
  };

  const findSubreddits = async (keywords: Keyword[]) => {
    try {
      const response = await fetch('http://localhost:8000/suggest_subreddits', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
          keywords: keywords  // Send the entire keywords array
        }),
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      setSubreddits(data.subreddits);
    } catch (err) {
      console.error("Error:", err);
      setError(`Failed to find subreddits: ${err instanceof Error ? err.message : 'Unknown error'}`);
    }
  };

  return (
    <div className="landing-page">
      <ul className="components-list">
        <li>
          <h1>Reddit Community Finder</h1>
        </li>
        
        <li>
          <textarea
            placeholder="Tell us about your idea..."
            className="idea-input"
            value={ideaDescription}
            onChange={(e) => setIdeaDescription(e.target.value)}
            rows={4}
          />
        </li>
        
        <li>
          <button 
            className="custom-button"
            onClick={generateKeywords}
            disabled={loading || !ideaDescription.trim()}
          >
            {loading ? "Analyzing..." : "Generate Keywords"}
          </button>
        </li>

        {error && <li className="error-message">{error}</li>}

        {keywords.length > 0 && (
          <li className="keywords-container">
            <h2>Generated Keywords</h2>
            <div className="keywords-pills">
              {keywords.map((keyword, index) => (
                <span key={index} className="keyword-pill">
                  {keyword.text}
                </span>
              ))}
            </div>
          </li>
        )}

        {subreddits.length > 0 && (
          <li className="subreddits-container">
            <h2>Suggested Communities</h2>
            <div className="subreddit-pills">
              {subreddits.map((subreddit, index) => (
                <a
                  key={index}
                  href={`https://reddit.com/r/${subreddit.name}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="subreddit-pill"
                >
                  r/{subreddit.name}
                  <span className="subscriber-count">
                    {subreddit.subscribers.toLocaleString()} members
                  </span>
                </a>
              ))}
            </div>
          </li>
        )}
      </ul>
    </div>
  );
};

export default LandingPage;
