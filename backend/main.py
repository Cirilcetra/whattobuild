import os
import json
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
import praw
from dotenv import load_dotenv
from pydantic import BaseModel
from typing import List
from subreddit import search_subreddits

# Load environment variables
load_dotenv()

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize OpenAI and Reddit clients
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
reddit = praw.Reddit(
    client_id=os.getenv("REDDIT_CLIENT_ID"),
    client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
    user_agent="python:reddit_analyzer:v1.0 (by /u/your_username)"
)

class IdeaDescription(BaseModel):
    description: str

class Keyword(BaseModel):
    text: str
    relevance: float

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
async def fetch_reddit(subreddit: str, limit: int = 10):
    """Fetches posts from a subreddit and categorizes insights using AI."""
    
    try:
        posts = []
        
        for post in reddit.subreddit(subreddit).hot(limit=limit):
            posts.append({
                "id": post.id,
                "title": post.title,
                "text": post.selftext[:500],  # Truncate long posts for efficiency
                "score": post.score,
                "url": post.url,
                "comments": post.num_comments,
                "author": str(post.author) if post.author else "[deleted]",
                "created_utc": post.created_utc
            })

        if not posts:
            return {"success": False, "error": "No posts found"}

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
async def generate_keywords(idea: IdeaDescription) -> dict:
    """Generates relevant keywords from an idea description using OpenAI."""
    
    try:
        prompt = f"""Given the following product or business idea, generate relevant keywords.
        Format the response as a JSON array of objects, each with 'text' and 'relevance' (0-1) properties.
        Include only the most relevant 5-8 keywords.

        Idea: {idea.description}

        Example format:
        [
            {{"text": "productivity", "relevance": 0.9}},
            {{"text": "automation", "relevance": 0.8}}
        ]
        
        Provide only the JSON array, no additional text."""

        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a keyword extraction specialist."},
                {"role": "user", "content": prompt}
            ],
            response_format={ "type": "json_object" }
        )

        # Parse the response and ensure it's in the correct format
        keywords_data = json.loads(response.choices[0].message.content)
        
        # If the response is wrapped in an object, extract the keywords array
        keywords = keywords_data.get('keywords', keywords_data) if isinstance(keywords_data, dict) else keywords_data
        
        return {
            "success": True,
            "keywords": keywords
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/suggest_subreddits")
async def suggest_subreddits(keywords: dict) -> dict:
    """Find relevant subreddits based on keywords using Google Search API."""
    try:
        # Extract keyword texts from the array of keyword objects
        keyword_texts = []
        for keyword in keywords.get("keywords", []):
            if isinstance(keyword, dict) and "text" in keyword:
                keyword_texts.append(keyword["text"])
            elif isinstance(keyword, str):
                keyword_texts.append(keyword)
        
        if not keyword_texts:
            raise HTTPException(status_code=400, detail="No valid keywords provided")
            
        # Get subreddit suggestions
        subreddit_names = search_subreddits(keyword_texts)
        
        # For each subreddit, get basic info
        subreddits = []
        for name in subreddit_names:
            try:
                subreddit = reddit.subreddit(name)
                subreddits.append({
                    "name": name,
                    "description": subreddit.public_description[:200] if subreddit.public_description else "",
                    "subscribers": subreddit.subscribers
                })
            except Exception as e:
                print(f"Error fetching info for r/{name}: {str(e)}")
                continue
        
        return {
            "success": True,
            "subreddits": subreddits
        }
    except Exception as e:
        print(f"Error in suggest_subreddits: {str(e)}")  # Add debug logging
        raise HTTPException(status_code=500, detail=str(e)) 