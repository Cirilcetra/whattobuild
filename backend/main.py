import os
import json
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from openai import OpenAI
import praw
from dotenv import load_dotenv
from pydantic import BaseModel
from typing import List, Optional, Dict

# Use relative imports since we're in a package
from .subreddit import search_subreddits, get_subreddit_posts
from .chromadb import RedditPostStore

# Load environment variables
load_dotenv()

app = FastAPI()

# Update CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Your React app's URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# Initialize OpenAI and Reddit clients
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
reddit = praw.Reddit(
    client_id=os.getenv("REDDIT_CLIENT_ID"),
    client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
    user_agent="python:reddit_analyzer:v1.0 (by /u/your_username)"
)

# Initialize RedditPostStore
post_store = RedditPostStore()

class IdeaDescription(BaseModel):
    description: str

class Keyword(BaseModel):
    text: str
    relevance: float

class ErrorResponse(BaseModel):
    success: bool = False
    error: str

class SubredditResponse(BaseModel):
    success: bool = True
    subreddits: List[Dict]

class AnalysisResponse(BaseModel):
    success: bool = True
    category: str
    subreddit: Optional[str]
    analysis: str

async def analyze_reddit_posts(posts):
    """Analyzes Reddit posts and categorizes them into structured insights."""
    
    prompt = f"""You are an AI that extracts insights from Reddit discussions.
Your task is to categorize posts into five key areas:

1. **Most Requested Ideas** – Highly desired products, features, or solutions.
2. **Most Frustrating Problems** – Issues users frequently complain about.
3. **Most Upvoted Suggestions** – Popular and well-supported recommendations.
4. **AI-Solvable Ideas** – Recurring issues where AI automation can provide a solution.
5. **Recurring Problems** – Common concerns that repeatedly appear across discussions.

### Example Format:
{{
    "mostRequestedIdeas": ["Feature X for productivity", "New tool for task automation"],
    "mostFrustratingProblems": ["Existing software is too expensive", "Lack of integrations"],
    "mostUpvotedSuggestions": ["Use open-source alternatives", "Redesign of UI"],
    "aiSolvableIdeas": ["Automating customer support", "AI-powered content recommendations"],
    "recurringProblems": ["Data privacy concerns", "High subscription costs"]
}}

### Posts Data (Analyze and extract key points):
{posts}

Provide a structured JSON response only. Do not include explanations."""

    response = openai_client.chat.completions.create(
        model="gpt-3.5-turbo",  # Changed to gpt-3.5-turbo as it's more widely available
        messages=[
            {"role": "system", "content": "You are a research assistant specializing in data analysis."},
            {"role": "user", "content": prompt}
        ],
        response_format={ "type": "json_object" }
    )

    return response.choices[0].message.content

@app.get("/fetch_reddit/{subreddit}")
async def fetch_reddit(subreddit: str, limit: int = 100):
    """Fetches posts from a subreddit, stores them in ChromaDB, and returns insights."""
    
    try:
        posts = []
        
        for post in reddit.subreddit(subreddit).hot(limit=limit):
            posts.append({
                "id": post.id,
                "title": post.title,
                "text": post.selftext[:500],  # Truncate long posts
                "score": post.score,
                "url": post.url,
                "comments": post.num_comments,
                "author": str(post.author) if post.author else "[deleted]",
                "created_utc": post.created_utc,
                "subreddit": subreddit
            })

        if not posts:
            return {"success": False, "error": "No posts found"}

        # Store posts in ChromaDB
        post_store.store_posts(posts)

        # Get analysis using the stored posts
        analysis = await analyze_reddit_posts(posts)
        
        return {
            "success": True,
            "subreddit": subreddit,
            "total_posts_analyzed": len(posts),
            "analysis": analysis
        }
    
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/generate_keywords")
async def generate_keywords(description: dict):
    try:
        prompt = f"""Given the following product or business idea, generate relevant keywords to find relavant reddit communities that align with the idea.Make sure the keywords communicate the idea in a way that is easy to find on reddit.
        Format the response as a JSON object with a 'keywords' array containing objects with 'text' and 'relevance' properties.
        Include only the most relevant 5-8 keywords.

        Idea: {description['description']}

        Example format:
        {{
            "keywords": [
                {{"text": "productivity", "relevance": 0.9}},
                {{"text": "automation", "relevance": 0.8}}
            ]
        }}
        
        Provide only the JSON object, no additional text."""

        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a keyword extraction specialist."},
                {"role": "user", "content": prompt}
            ],
            response_format={ "type": "json_object" }
        )

        # Parse the response
        keywords_data = json.loads(response.choices[0].message.content)
        
        # Ensure the response has the expected structure
        if not isinstance(keywords_data, dict) or 'keywords' not in keywords_data:
            keywords_data = {'keywords': keywords_data}

        return JSONResponse(content={"success": True, "keywords": keywords_data['keywords']})

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )

@app.post("/suggest_subreddits")
async def suggest_subreddits(request: dict) -> JSONResponse:
    """Find relevant subreddits based on keywords."""
    try:
        # Extract keyword texts
        keywords = request.get("keywords", [])
        keyword_texts = []
        
        for keyword in keywords:
            if isinstance(keyword, dict) and "text" in keyword:
                keyword_texts.append(keyword["text"])
            elif isinstance(keyword, str):
                keyword_texts.append(keyword)
        
        if not keyword_texts:
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": "No valid keywords provided"}
            )
            
        print("Searching with keywords:", keyword_texts)  # Debug log
        subreddits = await search_subreddits(keyword_texts)
        
        if not subreddits:
            return JSONResponse(
                content={
                    "success": True,
                    "subreddits": [],
                    "message": "No subreddits found"
                }
            )
            
        return JSONResponse(
            content={
                "success": True,
                "subreddits": subreddits
            }
        )
    except Exception as e:
        print(f"Error in suggest_subreddits: {str(e)}")  # Debug log
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )

@app.get("/posts/{category}")
async def get_posts_by_category(
    category: str,
    subreddit: Optional[str] = None,
    limit: int = 10
):
    """Fetches posts from ChromaDB based on category and optionally filtered by subreddit"""
    try:
        posts = post_store.get_posts_by_category(
            category=category,
            subreddit=subreddit,
            limit=limit
        )
        
        return {
            "success": True,
            "category": category,
            "subreddit": subreddit,
            "posts": posts
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/analyze/{category}", response_model=AnalysisResponse)
async def analyze_category(
    category: str,
    subreddit: Optional[str] = None
):
    """Analyzes posts in a category using LangChain and GPT"""
    try:
        analysis = await post_store.analyze_category(
            category=category,
            subreddit=subreddit
        )
        
        return {
            "success": True,
            "category": category,
            "subreddit": subreddit,
            "analysis": analysis
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/search")
async def search(query: str) -> List[Dict]:
    try:
        return search_subreddits(query)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/posts/{subreddit}")
async def get_posts(subreddit: str) -> List[Dict]:
    try:
        return get_subreddit_posts(subreddit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 