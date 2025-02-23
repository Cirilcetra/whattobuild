import requests
import os
from dotenv import load_dotenv
import json
import traceback

# Load environment variables
load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
SEARCH_ENGINE_ID = os.getenv("GOOGLE_CX")

def search_subreddits(keywords):
    """
    Search for relevant subreddits using Google Custom Search API.
    Returns a list of up to 6 most relevant subreddit names.
    """
    try:
        if not GOOGLE_API_KEY or not SEARCH_ENGINE_ID:
            print("API Credentials Check:")
            print(f"API Key present: {'Yes' if GOOGLE_API_KEY else 'No'}")
            print(f"Search Engine ID present: {'Yes' if SEARCH_ENGINE_ID else 'No'}")
            return ["freelance", "WorkOnline", "digitalnomad"]
            
        # Clean and prepare keywords
        cleaned_keywords = [k.strip() for k in keywords if k.strip()]
        print(f"Cleaned keywords: {cleaned_keywords}")
        
        if not cleaned_keywords:
            return ["freelance", "WorkOnline", "digitalnomad"]
            
        # Join keywords with OR for broader search
        query = f"site:reddit.com/r/ {' OR '.join(cleaned_keywords)}"
        print(f"Search query: {query}")
        
        url = "https://www.googleapis.com/customsearch/v1"
        params = {
            "key": GOOGLE_API_KEY,
            "cx": SEARCH_ENGINE_ID,
            "q": query,
            "num": 10
        }
        
        print("Making Google API request...")
        response = requests.get(url, params=params)
        print(f"Response status: {response.status_code}")
        
        if response.status_code != 200:
            print(f"Error response: {response.text}")
            return ["freelance", "WorkOnline", "digitalnomad"]
            
        data = response.json()
        
        if "error" in data:
            print(f"Google API error: {json.dumps(data['error'], indent=2)}")
            return ["freelance", "WorkOnline", "digitalnomad"]
            
        if "items" not in data:
            print("No search results found")
            print(f"Response data: {json.dumps(data, indent=2)[:500]}...")
            return ["freelance", "WorkOnline", "digitalnomad"]
            
        subreddits = set()
        for item in data["items"]:
            link = item.get("link", "")
            if "reddit.com/r/" in link:
                parts = link.split("reddit.com/r/")
                if len(parts) > 1:
                    subreddit = parts[1].split("/")[0].lower()
                    if subreddit and subreddit not in ["submit", "search", "popular", "all"]:
                        subreddits.add(subreddit)
                        print(f"Found subreddit: {subreddit}")
        
        if not subreddits:
            print("No valid subreddits found in results")
            return ["freelance", "WorkOnline", "digitalnomad"]
            
        result = list(subreddits)[:6]
        print(f"Returning subreddits: {result}")
        return result
        
    except Exception as e:
        print(f"Error in search_subreddits: {str(e)}")
        print(f"Full traceback: {traceback.format_exc()}")
        return ["freelance", "WorkOnline", "digitalnomad"]

# Remove the test code from the module
# keywords = ["freelancing", "side hustle", "passive income"]
# print(search_subreddits(keywords))
