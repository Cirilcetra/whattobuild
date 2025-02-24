import chromadb
import os
from dotenv import load_dotenv
from .subreddit import get_subreddit_posts
import logging
from openai import OpenAI
import time
import math
import json
from typing import List, Dict

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

CATEGORY_MAPPINGS = {
    "ideas": "Most Requested Ideas",
    "problems": "Common Problems",
    "suggestions": "Popular Suggestions",
    "ai_solvable": "AI-Solvable Ideas"
}

class RedditPostStore:
    def __init__(self):
        try:
            self.client = chromadb.PersistentClient(path="./chroma_db")
            self.collection = self.client.get_or_create_collection(
                name="reddit_posts",
                metadata={"hnsw:space": "cosine"}
            )
            self.openai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            logger.info("Successfully initialized RedditPostStore")
        except Exception as e:
            logger.error(f"Failed to initialize RedditPostStore: {str(e)}")
            raise

    async def analyze_category(self, category: str, subreddit: str) -> Dict:
        """Analyze subreddit posts with smart filtering and classification"""
        try:
            # Get relevant posts from ChromaDB using similarity search
            category_embedding = await self.get_embedding(category)
            results = self.collection.query(
                query_embeddings=[category_embedding],
                n_results=10,  # Limit to top 10 most relevant posts
                where={"subreddit": subreddit} if subreddit else None
            )
            
            if not results['documents'][0]:  # Check if we got any results
                return {
                    "success": False,
                    "analysis": json.dumps({
                        "error": f"No relevant posts found for r/{subreddit}",
                        "classification": {
                            "solution_requests": [],
                            "pain_points": [],
                            "app_ideas": [],
                            "ai_solvable": []
                        },
                        "summary": "No data available",
                        "metadata": {
                            "total_posts": 0,
                            "analyzed_posts": 0,
                            "average_relevance": 0,
                            "subreddit": subreddit,
                            "category": category
                        }
                    }),
                    "metadata": {
                        "subreddit": subreddit,
                        "category": category
                    }
                }

            # Format posts for analysis
            posts_text = "\n\n".join([
                f"Title: {meta.get('title', '')}\nContent: {doc}"
                for doc, meta in zip(results['documents'][0], results['metadatas'][0])
            ])

            # Prepare classification prompt
            classification_prompt = {
                "type": "object",
                "properties": {
                    "solution_requests": {
                        "type": "array",
                        "description": "Most requested features, products, or solutions from the community",
                        "items": {"type": "string"}
                    },
                    "pain_points": {
                        "type": "array",
                        "description": "Common problems and pain points discussed in the community",
                        "items": {"type": "string"}
                    },
                    "app_ideas": {
                        "type": "array",
                        "description": "Popular suggestions and recommendations from the community",
                        "items": {"type": "string"}
                    },
                    "ai_solvable": {
                        "type": "array",
                        "description": "Problems or ideas that could be solved with AI technology",
                        "items": {"type": "string"}
                    }
                }
            }

            # Classify posts using OpenAI function calling
            response = self.openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a product analyst providing concise, actionable insights."},
                    {"role": "user", "content": f"Analyze these relevant Reddit posts and categorize them:\n\n{posts_text}"}
                ],
                functions=[{"name": "classify", "parameters": classification_prompt}],
                function_call={"name": "classify"}
            )

            # Generate summary using a separate call
            summary_prompt = f"Provide a brief summary of the main trends and insights from r/{subreddit} based on these posts. Focus on product/market implications."
            
            summary_response = self.openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a product analyst providing concise, actionable insights."},
                    {"role": "user", "content": f"{summary_prompt}\n\n{posts_text}"}
                ]
            )

            analysis_dict = {
                "classification": json.loads(response.choices[0].message.function_call.arguments),
                "summary": summary_response.choices[0].message.content,
                "metadata": {
                    "total_posts": len(results['documents'][0]),
                    "analyzed_posts": len(results['documents'][0]),
                    "average_relevance": sum(1 - dist for dist in results['distances'][0]) / len(results['distances'][0]),
                    "subreddit": subreddit,
                    "category": category
                }
            }

            return {
                "success": True,
                "analysis": json.dumps(analysis_dict),  # Convert to string
                "metadata": {
                    "subreddit": subreddit,
                    "category": category
                }
            }

        except Exception as e:
            error_msg = f"Error analyzing r/{subreddit}: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "analysis": json.dumps({"error": error_msg}),  # Convert to string
                "metadata": {
                    "subreddit": subreddit,
                    "category": category
                }
            }

    async def store_posts(self, posts: List[Dict]) -> None:
        """Store Reddit posts in ChromaDB"""
        try:
            documents = []
            ids = []
            embeddings = []
            metadatas = []
            
            for post in posts:
                text = f"Title: {post['title']}\n\nContent: {post.get('selftext', '')}"
                embedding = await self.get_embedding(text)
                
                documents.append(text)
                ids.append(post["id"])
                embeddings.append(embedding)
                metadatas.append({
                    "score": post.get("score", 0),
                    "num_comments": post.get("num_comments", 0),
                    "created_utc": post.get("created_utc", 0),
                    "subreddit": post.get("subreddit", ""),
                    "url": post.get("url", "")
                })
            
            self.collection.upsert(
                documents=documents,
                ids=ids,
                embeddings=embeddings,
                metadatas=metadatas
            )
            logger.info(f"Successfully stored {len(posts)} posts")
            
        except Exception as e:
            logger.error(f"Error storing posts: {str(e)}")
            raise

    async def get_embedding(self, text: str) -> List[float]:
        """Get embeddings using OpenAI API"""
        try:
            if isinstance(text, list):
                text = "\n".join(text)
            response = self.openai.embeddings.create(
                input=text,
                model="text-embedding-ada-002"
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Error generating embedding: {str(e)}")
            raise

    async def search_similar(self, query: str, k: int = 5) -> List[Dict]:
        """Search for similar posts"""
        query_embedding = await self.get_embedding(query)
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=k,
            include=["documents", "metadatas", "distances"]
        )
        
        return [
            {
                "content": doc,
                "metadata": meta,
                "score": 1 - dist  # Convert distance to similarity score
            }
            for doc, meta, dist in zip(
                results['documents'][0],
                results['metadatas'][0],
                results['distances'][0]
            )
        ]

    def cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = math.sqrt(sum(a * a for a in vec1))
        norm2 = math.sqrt(sum(b * b for b in vec2))
        return dot_product / (norm1 * norm2)
