import React, { useState } from "react";
import "./landingpage.css"; // Import the CSS file with correct name
import { analyzeRedditPosts, AnalysisResult } from "../openai/openai";
import ReactMarkdown from 'react-markdown';

interface Keyword {
  text: string;
  relevance: number;
}

interface SubredditSuggestion {
  name: string;
  description: string;
  subscribers: number;
}

interface Classification {
  solution_requests: string[];
  pain_points: string[];
  app_ideas: string[];
  ai_solvable: string[];
  [key: string]: string[];  // Add index signature
}

interface RedditAnalysis {
  category: string;
  analysis: {
    classification: Classification;
    summary: string;
    metadata: {
      total_posts: number;
      analyzed_posts: number;
      average_relevance: number;
      subreddit: string;
      category: string;
    };
  };
  subreddit?: string;
}

const CATEGORY_MAPPINGS: { [key: string]: string } = {
  solution_requests: "Most Requested Ideas",
  pain_points: "Common Problems",
  app_ideas: "Popular Suggestions",
  ai_solvable: "AI-Solvable Ideas"
};

const truncateToWords = (text: string, wordLimit: number) => {
  const words = text.split(' ');
  if (words.length > wordLimit) {
    return words.slice(0, wordLimit).join(' ') + '...';
  }
  return text;
};

const LandingPage = (): JSX.Element => {
  const [ideaDescription, setIdeaDescription] = useState("");
  const [keywords, setKeywords] = useState<Keyword[]>([]);
  const [subreddits, setSubreddits] = useState<SubredditSuggestion[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [selectedSubreddit, setSelectedSubreddit] = useState<string>("");
  const [analysis, setAnalysis] = useState<RedditAnalysis | null>(null);
  const [activeCategory, setActiveCategory] = useState<string>("solution_requests");
  const [fetchData, setFetchData] = useState<{ total_posts_analyzed: number } | null>(null);

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

  const analyzeSubreddit = async (subredditName: string) => {
    setLoading(true);
    setError("");
    setFetchData(null);
    
    try {
        const fetchResponse = await fetch(`http://localhost:8000/fetch_reddit/${subredditName}`);
        const fetchDataResponse = await fetchResponse.json();
        setFetchData(fetchDataResponse);
        
        if (!fetchDataResponse.success) {
            throw new Error(fetchDataResponse.error || 'Failed to fetch subreddit posts');
        }

        const analysisResponse = await fetch(
            `http://localhost:8000/analyze/${activeCategory}?subreddit=${subredditName}`
        );
        const analysisData = await analysisResponse.json();
        
        if (analysisData.success) {
            setAnalysis({
                category: analysisData.category,
                analysis: analysisData.analysis,
                subreddit: analysisData.subreddit
            });
            setSelectedSubreddit(subredditName);
        } else {
            throw new Error(analysisData.error || 'Failed to analyze subreddit');
        }
    } catch (err) {
        console.error("Error:", err);
        setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
        setLoading(false);
    }
  };

  const categories = [
    { id: "solution_requests", label: "Most Requested Ideas" },
    { id: "pain_points", label: "Common Problems" },
    { id: "app_ideas", label: "Popular Suggestions" },
    { id: "ai_solvable", label: "AI-Solvable Ideas" }
  ];

  return (
    <div className="landing-page">
      <ul className="components-list">
        <li>
          <h1>Reddit Idea Validator</h1>
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
              <h2>Select a Subreddit</h2>
              <div className="subreddit-pills-wrapper">
                <div className="subreddit-pills">
                  {subreddits.map((subreddit, index) => (
                    <button
                      key={index}
                      onClick={() => analyzeSubreddit(subreddit.name)}
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

              {/* Analysis Container nested inside subreddits-container */}
              {(loading || analysis) && (
                <div className="analysis-container">
                  {loading ? (
                    <div className="loading">
                      <div className="loading-spinner"></div>
                      <p>Analyzing subreddit...</p>
                      {fetchData?.total_posts_analyzed && (
                        <p>Fetched {fetchData.total_posts_analyzed} posts</p>
                      )}
                    </div>
                  ) : analysis && (
                    <div className="analysis-content">
                      <div className="community-summary">
                        <h2>Community Insights</h2>
                        <ReactMarkdown
                          components={{
                            p: ({children}) => <p className="summary-text">{children}</p>
                          }}
                        >
                          {truncateToWords(analysis.analysis.summary, 100)}
                        </ReactMarkdown>
                      </div>
                      
                      <div className="tabs">
                        {Object.entries(CATEGORY_MAPPINGS).map(([key, label]) => (
                          <button
                            key={key}
                            className={`tab-button ${activeCategory === key ? 'active' : ''}`}
                            onClick={() => setActiveCategory(key)}
                          >
                            {label}
                          </button>
                        ))}
                      </div>

                      <div className="tab-content">
                        {analysis.analysis.classification[activeCategory]?.length > 0 ? (
                          analysis.analysis.classification[activeCategory].map((item, index) => (
                            <div key={index} className="insight-item">
                              {item}
                            </div>
                          ))
                        ) : (
                          <div className="no-data">No insights available for this category</div>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          </li>
        )}
      </ul>
    </div>
  );
};

export default LandingPage;

