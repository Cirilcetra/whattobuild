import asyncpraw
from typing import List, Dict
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Initialize AsyncPRAW client
async def get_reddit_client():
    return asyncpraw.Reddit(
        client_id=os.getenv('REDDIT_CLIENT_ID'),
        client_secret=os.getenv('REDDIT_CLIENT_SECRET'),
        user_agent=os.getenv('REDDIT_USER_AGENT', 'MyBot/1.0')
    )

async def search_subreddits(query: str | List[str]) -> List[Dict]:
    """Search for subreddits using multiple Reddit API approaches."""
    try:
        # Get async Reddit client
        reddit = await get_reddit_client()
        
        # Extract search terms
        if isinstance(query, list):
            print(f"Original keywords: {query}")  # Debug log
            
            # Extract words and phrases
            search_terms = set()  # Use set to avoid duplicates
            for keyword in query:
                if isinstance(keyword, dict):
                    text = keyword.get('text', '').lower().strip()
                else:
                    text = str(keyword).lower().strip()
                search_terms.add(text)
            
            print(f"Search terms: {search_terms}")  # Debug log
            
            # Create individual searches for each term
            all_subreddits = []
            seen_subreddits = set()
            
            # First search with exact phrases
            for term in search_terms:
                try:
                    print(f"Searching for term: {term}")  # Debug log
                    async for subreddit in reddit.subreddits.search(f'"{term}"', limit=15):
                        try:
                            subscriber_count = getattr(subreddit, 'subscribers', 0)
                            if subscriber_count is None:
                                subscriber_count = 0
                                
                            if (subscriber_count >= 5000 and 
                                subreddit.display_name.lower() not in seen_subreddits):
                                seen_subreddits.add(subreddit.display_name.lower())
                                
                                description = getattr(subreddit, 'description', '')
                                if description is None:
                                    description = ''
                                    
                                # Calculate relevance score based on term presence in name/description
                                relevance_score = 0
                                if term in subreddit.display_name.lower():
                                    relevance_score += 2
                                if term in description.lower():
                                    relevance_score += 1
                                
                                all_subreddits.append({
                                    "name": subreddit.display_name,
                                    "description": description[:200] if description else "",
                                    "subscribers": subscriber_count,
                                    "url": f"https://reddit.com/r/{subreddit.display_name}",
                                    "relevance_score": relevance_score,
                                    "matched_term": term
                                })
                                print(f"Found subreddit: r/{subreddit.display_name} ({subscriber_count} subscribers)")
                                
                        except AttributeError as e:
                            print(f"Error processing subreddit attributes: {e}")
                            continue
                except Exception as e:
                    print(f"Error searching term '{term}': {e}")
                    continue
            
            # Sort by relevance score and subscriber count
            all_subreddits.sort(key=lambda x: (
                -x.get('relevance_score', 0),  # Higher relevance first
                -x['subscribers']  # Then by subscriber count
            ))
            
            print(f"Found {len(all_subreddits)} total subreddits")  # Debug log
            
            # Close the client
            await reddit.close()
            return all_subreddits[:10]  # Return top 10 results
            
        else:
            # Handle single string query
            search_query = str(query).lower().strip()
            subreddits = []
            seen_subreddits = set()
            
            async for subreddit in reddit.subreddits.search(search_query, limit=20):
                try:
                    subscriber_count = getattr(subreddit, 'subscribers', 0)
                    if subscriber_count is None:
                        subscriber_count = 0
                        
                    if (subscriber_count >= 5000 and 
                        subreddit.display_name.lower() not in seen_subreddits):
                        seen_subreddits.add(subreddit.display_name.lower())
                        
                        description = getattr(subreddit, 'description', '')
                        if description is None:
                            description = ''
                            
                        subreddits.append({
                            "name": subreddit.display_name,
                            "description": description[:200] if description else "",
                            "subscribers": subscriber_count,
                            "url": f"https://reddit.com/r/{subreddit.display_name}"
                        })
                except AttributeError as e:
                    print(f"Error processing subreddit: {e}")
                    continue
            
            # Close the client
            await reddit.close()
            return subreddits[:10]  # Return top 10 results

    except Exception as e:
        print(f"Main search error: {e}")  # Debug log
        if 'reddit' in locals():
            await reddit.close()
        return []

async def get_subreddit_posts(subreddit_name: str, limit: int = 100) -> List[Dict]:
    """Get posts from a specific subreddit."""
    try:
        reddit = await get_reddit_client()
        subreddit = await reddit.subreddit(subreddit_name)
        posts = []
        
        async for post in subreddit.hot(limit=limit):
            try:
                posts.append({
                    "id": post.id,
                    "title": post.title,
                    "selftext": post.selftext[:500] if post.selftext else "",  # Truncate long posts
                    "score": post.score,
                    "url": post.url,
                    "num_comments": post.num_comments,
                    "author": str(post.author) if post.author else "[deleted]",
                    "created_utc": post.created_utc,
                    "subreddit": subreddit_name
                })
            except Exception as e:
                print(f"Error processing post: {str(e)}")
                continue

        await reddit.close()
        return posts

    except Exception as e:
        print(f"Error in get_subreddit_posts: {str(e)}")
        return []

# Remove the test code from the module
# keywords = ["freelancing", "side hustle", "passive income"]
# print(search_subreddits(keywords))
