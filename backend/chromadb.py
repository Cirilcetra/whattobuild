from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
from langchain.chat_models import ChatOpenAI
from langchain.chains import RetrievalQA
from typing import List, Dict, Optional
import os
from dotenv import load_dotenv
from .subreddit import get_subreddit_posts  # Add the dot for relative import

# Load environment variables
load_dotenv()

class RedditPostStore:
    def __init__(self):
        self.embeddings = OpenAIEmbeddings(openai_api_key=os.getenv("OPENAI_API_KEY"))
        self.vectorstore = Chroma(
            collection_name="reddit_posts",
            embedding_function=self.embeddings,
            persist_directory="./data"
        )
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )
        self.llm = ChatOpenAI(
            model_name="gpt-3.5-turbo",
            temperature=0,
            openai_api_key=os.getenv("OPENAI_API_KEY")
        )
        
        # Initialize QA chain
        self.qa_chain = RetrievalQA.from_chain_type(
            llm=self.llm,
            retriever=self.vectorstore.as_retriever(
                search_kwargs={"k": 50}  # Fetch top 50 relevant posts
            )
        )

    async def analyze_category(self, category: str, subreddit: Optional[str] = None) -> str:
        """Analyze posts for a specific category using LangChain and GPT"""
        try:
            if subreddit:
                # Fetch and store posts for the subreddit
                posts = await get_subreddit_posts(subreddit)
                if posts:
                    self.store_posts(posts)
                else:
                    return f"No posts found in r/{subreddit}"

            # Define category-specific prompts
            category_prompts = {
                "ideas": (
                    "Based on the Reddit posts, what are the most requested features "
                    "and ideas in this community? List the top 3-5 most common requests."
                ),
                "problems": (
                    "What are the most common problems and frustrations users discuss "
                    "in this community? List the top 3-5 most mentioned issues."
                ),
                "suggestions": (
                    "What are the most upvoted suggestions and recommendations shared "
                    "in this community? List the top 3-5 most popular suggestions."
                ),
                "ai_solvable": (
                    "Looking at the discussions, what problems or needs could potentially "
                    "be solved with AI automation? List 3-5 specific opportunities."
                )
            }

            prompt = category_prompts.get(category, "")
            if subreddit:
                prompt += f" Focus specifically on posts from r/{subreddit}."

            # Create a new QA chain for each query
            qa_chain = RetrievalQA.from_chain_type(
                llm=self.llm,
                retriever=self.vectorstore.as_retriever(
                    search_kwargs={"k": 30}  # Fetch top 30 relevant posts
                )
            )

            response = await qa_chain.ainvoke({"query": prompt})
            return response["result"]

        except Exception as e:
            print(f"Error analyzing category: {str(e)}")
            return f"Error analyzing r/{subreddit}: {str(e)}"

    def store_posts(self, posts: List[Dict]) -> None:
        """Store Reddit posts in ChromaDB"""
        try:
            documents = []
            for post in posts:
                text = f"Title: {post['title']}\n\nContent: {post.get('selftext', '')}"
                metadata = {
                    "score": post.get("score", 0),
                    "num_comments": post.get("num_comments", 0),
                    "created_utc": post.get("created_utc", 0),
                    "subreddit": post.get("subreddit", ""),
                    "url": post.get("url", ""),
                    "id": post.get("id", "")
                }
                documents.append(Document(page_content=text, metadata=metadata))
            
            texts = self.text_splitter.split_documents(documents)
            self.vectorstore.add_documents(texts)
            
        except Exception as e:
            print(f"Error storing posts: {str(e)}")
            raise

    def search_similar(self, query: str, k: int = 5) -> List[Dict]:
        """Search for similar posts"""
        results = self.vectorstore.similarity_search_with_relevance_scores(query, k=k)
        return [
            {
                "content": doc.page_content,
                "metadata": doc.metadata,
                "score": score
            }
            for doc, score in results
        ]
