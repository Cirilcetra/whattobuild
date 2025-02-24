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

interface RedditAnalysis {
  category: string;
  analysis: string;
  subreddit?: string;
}

const LandingPage = (): JSX.Element => {
  const [ideaDescription, setIdeaDescription] = useState("");
  const [keywords, setKeywords] = useState<Keyword[]>([]);
  const [subreddits, setSubreddits] = useState<SubredditSuggestion[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [selectedSubreddit, setSelectedSubreddit] = useState<string>("");
  const [analysis, setAnalysis] = useState<RedditAnalysis | null>(null);
  const [activeCategory, setActiveCategory] = useState<string>("ideas");

  const generateKeywords = async () => {
    if (!ideaDescription.trim()) return;
    
    setLoading(true);
    setError("");
    
    try {
      console.log("Sending request with:", ideaDescription); // Debug log
      const response = await fetch('http://localhost:8000/generate_keywords', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ description: ideaDescription }),
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      console.log("Received keywords:", data); // Debug log
      
      if (data.success && data.keywords) {
        setKeywords(data.keywords);
        await findSubreddits(data.keywords);
      }
    } catch (err) {
      console.error("Error:", err);
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  const findSubreddits = async (keywords: any[]) => {
    try {
      console.log("Finding subreddits for keywords:", keywords); // Debug log
      const response = await fetch('http://localhost:8000/suggest_subreddits', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        },
        body: JSON.stringify({ keywords }),
      });
      
      const data = await response.json();
      console.log("Response data:", data); // Debug log
      
      if (!response.ok) {
        throw new Error(data.error || `HTTP error! status: ${response.status}`);
      }
      
      if (data.success) {
        setSubreddits(data.subreddits || []);
        if (data.subreddits.length === 0) {
          setError("No relevant subreddits found");
        }
      } else {
        throw new Error(data.error || 'Failed to get subreddits');
      }
    } catch (err) {
      console.error("Error:", err);
      setError(err instanceof Error ? err.message : 'An error occurred');
    }
  };

  const analyzeSubreddit = async (subredditName: string, category: string) => {
    setLoading(true);
    setError("");
    
    try {
      const response = await fetch(
        `http://localhost:8000/analyze/${category}?subreddit=${subredditName}`
      );
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      if (data.success) {
        setAnalysis(data);
        setSelectedSubreddit(subredditName);
      } else {
        throw new Error(data.error);
      }
    } catch (err) {
      console.error("Error:", err);
      setError(`Failed to analyze subreddit: ${err instanceof Error ? err.message : 'Unknown error'}`);
    } finally {
      setLoading(false);
    }
  };

  const categories = [
    { id: "ideas", label: "Most Requested Ideas" },
    { id: "problems", label: "Common Problems" },
    { id: "suggestions", label: "Popular Suggestions" },
    { id: "ai_solvable", label: "AI-Solvable Ideas" }
  ];

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
          <li>
            <div className="subreddits-container">
              <h2>Suggested Communities</h2>
              <div className="subreddit-pills-wrapper">
                <div className="subreddit-pills">
                  {subreddits.map((subreddit, index) => (
                    <button
                      key={index}
                      onClick={() => analyzeSubreddit(subreddit.name, activeCategory)}
                      className={`subreddit-pill ${selectedSubreddit === subreddit.name ? 'active' : ''}`}
                    >
                      r/{subreddit.name}
                      <span className="subscriber-count">
                        {subreddit.subscribers.toLocaleString()} members
                      </span>
                    </button>
                  ))}
                </div>
              </div>

              {selectedSubreddit && (
                <>
                  <div className="category-tabs">
                    {categories.map(category => (
                      <button
                        key={category.id}
                        className={`category-tab ${activeCategory === category.id ? 'active' : ''}`}
                        onClick={() => {
                          setActiveCategory(category.id);
                          analyzeSubreddit(selectedSubreddit, category.id);
                        }}
                      >
                        {category.label}
                      </button>
                    ))}
                  </div>

                  <div className="content-area">
                    {loading ? (
                      <div className="loading">Analyzing subreddit...</div>
                    ) : analysis ? (
                      <div className="insight-item">
                        {analysis.analysis}
                      </div>
                    ) : null}
                  </div>
                </>
              )}
              
              <button className="test-button">
                Test my idea
              </button>
            </div>
          </li>
        )}
      </ul>
    </div>
  );
};

export default LandingPage;
