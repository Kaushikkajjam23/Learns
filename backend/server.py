from fastapi import FastAPI, HTTPException, Request, Depends, status, File, UploadFile, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
import requests
from typing import Dict
from langchain.text_splitter import CharacterTextSplitter  # Add if not already imported
import json  # Add if not already imported
from typing import Dict  # Add if not already imported
from dotenv import load_dotenv
import os
import pathlib
import json
import logging
from datetime import timedelta, datetime
from typing import List, Optional
import uuid
from sqlalchemy.orm import Session
from bs4 import BeautifulSoup
from langchain.text_splitter import RecursiveCharacterTextSplitter
from chromadb import Client
from chromadb.config import Settings
from chromadb.utils import embedding_functions

# Import auth module
from auth import (
    Token, UserOut, UserCreate, authenticate_user, 
    create_access_token, get_current_active_user, create_user,
    ACCESS_TOKEN_EXPIRE_MINUTES
)

# Import database models
from database import (
    get_db, User, LearningPath, Subtopic, CompletedSubtopic, Resource
)

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins (you can specify specific origins if needed)
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)

# Load DIAL API key from environment variable
DIAL_API_KEY = os.getenv("DIAL_API_KEY")
DIAL_API_URL = "https://ai-proxy.lab.epam.com"

# Get the absolute path to the templates directory
BASE_DIR = pathlib.Path(__file__).parent.resolve()
templates_dir = BASE_DIR / "templates"

# Print debug info
print(f"Current working directory: {os.getcwd()}")
print(f"BASE_DIR: {BASE_DIR}")
print(f"Templates directory: {templates_dir}")
print(f"Templates directory exists: {templates_dir.exists()}")
if templates_dir.exists():
    print(f"Files in templates directory: {list(templates_dir.iterdir())}")

# Create a Jinja2Templates instance
templates = Jinja2Templates(directory=str(templates_dir))

# Add static files support if needed
static_dir = BASE_DIR / "static"
if not static_dir.exists():
    static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Initialize ChromaDB client with persistence
chroma_client = Client(Settings(
    anonymized_telemetry=False,
    is_persistent=True,
    persist_directory="chroma_store"
))
# Add this near the top of the file with other global variables
questions_store: List[str] = []  # Temporary in-memory store

# Set up sentence transformer embedding
sentence_transformer_ef = embedding_functions.SentenceTransformerEmbeddingFunction()

# Create or get collection
collection = chroma_client.get_or_create_collection(
    name="my_collection",
    embedding_function=sentence_transformer_ef
)

# Models
class TopicRequest(BaseModel):
    topic: str
    level: str
    component_id: str = None  # Field to track requesting component
    preferences: dict = None  # Add preferences field

class SubtopicModel(BaseModel):
    name: str
    explanation: str

class LearningPathResponse(BaseModel):
    id: str
    topic: str
    level: str
    overview: str
    subtopics: List[str]
    subtopics_detailed: List[SubtopicModel]
    roadmap: str
    estimated_hours: float
    progress: float
    created_at: datetime
    last_updated: datetime
    
    class Config:
        orm_mode = True

class ResourceRequest(BaseModel):
    type: str  # "image", "code", "reference", "video"
    content: str
    title: Optional[str] = None
    url: Optional[str] = None

class URLPayload(BaseModel):
    urls: List[str]

class QuestionPayload(BaseModel):
    question: str

# Helper functions for searching external content
def search_image(query):
    """Search for an image using a simple API"""
    try:
        # For demonstration purposes, we'll use Unsplash as a source
        # In production, use a proper image search API with authentication
        return f"https://source.unsplash.com/featured/?{query.replace(' ', ',')}"
    except Exception as e:
        logger.error(f"Error searching for image: {str(e)}")
        return None

def search_youtube_video(query):
    """Search for a YouTube video"""
    try:
        # For demonstration purposes - using common educational video IDs
        # In production, use the YouTube Data API
        video_ids = {
            "graph": "aIwKbUGiYzA",
            "types of graphs": "k1fsB9qHRkk",
            "directed graph": "5hPfm_uqXmw",
            "undirected graph": "eQA-m22wjTQ",
            "weighted graph": "09_LlHSGftU",
            "graph theory": "LFKZLXVO-Dg",
            "data structure": "9rhT3P1eT-Q",
            "algorithm": "ZA-tUyM_y7s",
            "machine learning": "ukzFI9rgwfU",
            "neural network": "bfmFfD2RIcg",
            "deep learning": "6M5VXKLf4D4",
            "python": "x7X9w_GIm1s",
            "javascript": "W6NZfCO5SIk",
            "react": "SqcY0GlETPk",
            "programming": "zOjov-2OZ0E",
        }
        
        # Try to match the query with predefined video IDs
        for key, video_id in video_ids.items():
            if key.lower() in query.lower():
                return f"https://www.youtube.com/watch?v={video_id}"
        
        # Default to YouTube search results if no match found
        return f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}"
    except Exception as e:
        logger.error(f"Error searching for video: {str(e)}")
        return None

def scrape_text_from_url(url: str) -> str:
    try:
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        return soup.get_text().strip()
    except Exception as e:
        print(f"Error scraping {url}: {e}")
        return ""

def query_epam_dial_llm(question: str, context: str) -> str:
    try:
        endpoint_url = f"{DIAL_API_URL}/openai/deployments/gpt-4o/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Api-Key": DIAL_API_KEY
        }
        params = {
            "api-version": "2023-12-01-preview"
        }
        data = {
            "messages": [
                {
                    "role": "user",
                    "content": f"Context:\n{context}\n\nQuestion: {question}"
                }
            ],
            "temperature": 0.7,
            "max_tokens": 1000
        }

        response = requests.post(endpoint_url, headers=headers, params=params, json=data, timeout=60)

        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
        else:
            print(f"LLM response error: {response.text}")
            return "LLM failed to respond correctly."
    except Exception as e:
        print(f"Exception querying LLM: {e}")
        return "LLM error."

def generate_roadmap(topic, subtopics):
    # A simple implementation to generate a roadmap based on subtopics
    roadmap = f"Learning Roadmap for {topic}:\n\n"
    for i, subtopic in enumerate(subtopics):
        roadmap += f"Step {i+1}: Master {subtopic}\n"
    return roadmap

# AI time estimation function
def estimate_learning_time(topic, level, subtopics):
    # Basic estimation logic - will be enhanced with AI
    base_hours = {
        "Junior": 2.0,
        "Intermediate": 1.5,
        "Senior": 1.0,
        "Lead": 0.8
    }
    
    base_time = base_hours.get(level, 1.5)
    total_hours = base_time * len(subtopics)
    
    # Adjust based on topic complexity (simple algorithm for now)
    complexity_factor = 1.0
    if len(topic.split()) > 3:  # More complex topics have more words
        complexity_factor = 1.2
    
    return round(total_hours * complexity_factor, 1)

# Authentication routes
@app.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/register", response_model=UserOut)
async def register_new_user(user_data: UserCreate, db: Session = Depends(get_db)):
    return create_user(db, user_data)

@app.get("/users/me", response_model=UserOut)
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    return current_user

# Existing routes
@app.get("/", response_class=HTMLResponse)
async def serve_index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/api/topics", response_model=LearningPathResponse)
async def submit_topic(
    request: TopicRequest, 
    http_request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    try:
        # Extract component ID from request headers or use the one provided in the request body
        component_id = request.component_id
        referer = http_request.headers.get("referer", "unknown")
        user_agent = http_request.headers.get("user-agent", "unknown")
        
        # Log the request information
        logger.info(f"Request received from component: {component_id}")
        logger.info(f"Request data: {request.dict()}")
        
        # Extract preferences
        preferences = request.preferences or {}
        include_images = preferences.get("includeImages", False)
        include_code = preferences.get("includeCode", False)
        include_references = preferences.get("includeReferences", False)
        include_videos = preferences.get("includeVideos", False)
        
        # Build prompt with preferences
        prompt = f"""
You are a helpful educational assistant. Provide a structured summary for the topic: "{request.topic}" at a {request.level} level.

Your response must follow this strict format:
---
Overview:
[overview content]

Subtopics:
1. [Subtopic 1]: [short explanation]
2. [Subtopic 2]: [short explanation]
3. [Subtopic 3]: [short explanation]
---

Additional preferences to consider:
"""

        if include_images:
            prompt += "- Include suggestions for relevant images or diagrams for each subtopic\n"
        if include_code:
            prompt += "- Include code examples where appropriate\n"
        if include_references:
            prompt += "- Include references to books, articles, or documentation\n"
        if include_videos:
            prompt += "- Include suggestions for video tutorials or courses\n"

        # Updated endpoint URL format
        endpoint_url = "https://ai-proxy.lab.epam.com/openai/deployments/gpt-4o/chat/completions"
        
        # Add API version as a query parameter
        params = {
            "api-version": "2023-12-01-preview"
        }
        
        # Updated headers format
        headers = {
            "Content-Type": "application/json",
            "Api-Key": DIAL_API_KEY  # Note: Using Api-Key instead of Authorization
        }

        # Updated request body format
        data = {
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.7,
            "max_tokens": 1500
        }

        # Make the request with timeout
        response = requests.post(
            endpoint_url, 
            headers=headers, 
            json=data,
            params=params,
            timeout=60  # Increased timeout to 60 seconds
        )

        # If there's an error in the response, raise an exception
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=response.text)

        # Extract the response text - adjust based on the actual response format
        response_data = response.json()
        text = response_data["choices"][0]["message"]["content"]

        # Parse the API response into overview and subtopics
        overview_match = text.split("Subtopics:")[0].strip()
        if "Overview:" in overview_match:
            overview_match = overview_match.split("Overview:")[1].strip()
            
        subtopics_block = text.split("Subtopics:\n")[-1]

        # Extract subtopic titles from the response
        subtopic_titles = []
        subtopics_with_explanations = []
        
        for line in subtopics_block.split("\n"):
            if line.strip() and line[0].isdigit():  # Check for numbered subtopics
                title = line[line.index(".") + 1:].strip().split(":")[0].strip()
                explanation = line.split(":", 1)[1].strip() if ":" in line else ""
                subtopic_titles.append(title)
                subtopics_with_explanations.append({"name": title, "explanation": explanation})

        # Generate a roadmap
        roadmap = generate_roadmap(request.topic, subtopic_titles)
        
        # Estimate learning time
        estimated_hours = estimate_learning_time(request.topic, request.level, subtopic_titles)
        
        # Create a unique ID for this learning path
        path_id = str(uuid.uuid4())
        current_time = datetime.utcnow()
        
        # Create learning path in database
        db_learning_path = LearningPath(
            id=path_id,
            user_id=current_user.id,
            topic=request.topic,
            level=request.level,
            overview=overview_match,
            roadmap=roadmap,
            estimated_hours=estimated_hours,
            progress=0.0,
            created_at=current_time,
            last_updated=current_time
        )
        
        db.add(db_learning_path)
        
        # Add subtopics to database
        for subtopic_data in subtopics_with_explanations:
            db_subtopic = Subtopic(
                learning_path_id=path_id,
                name=subtopic_data["name"],
                explanation=subtopic_data["explanation"]
            )
            db.add(db_subtopic)
        
        db.commit()
        
        # Prepare the response with component tracking information
        response_data = {
            "id": path_id,
            "topic": request.topic,
            "level": request.level,
            "overview": overview_match,
            "subtopics": subtopic_titles,
            "subtopics_detailed": subtopics_with_explanations,
            "roadmap": roadmap,
            "estimated_hours": estimated_hours,
            "progress": 0.0,
            "created_at": current_time,
            "last_updated": current_time,
            "request_metadata": {
                "requesting_component": component_id,
                "referer": referer,
                "user_agent": user_agent
            }
        }
        
        logger.info(f"Sending response for component: {component_id}")
        return response_data
        
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# New endpoints for the dashboard
@app.get("/api/learning-paths", response_model=List[LearningPathResponse])
async def get_learning_paths(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    # Get all learning paths for the current user
    db_paths = db.query(LearningPath).filter(LearningPath.user_id == current_user.id).all()
    
    # Prepare response data
    paths_data = []
    for path in db_paths:
        # Get subtopics for this path
        subtopics = db.query(Subtopic).filter(Subtopic.learning_path_id == path.id).all()
        subtopic_names = [s.name for s in subtopics]
        subtopics_detailed = [{"name": s.name, "explanation": s.explanation} for s in subtopics]
        
        # Get completed subtopics
        completed = db.query(CompletedSubtopic).filter(
            CompletedSubtopic.learning_path_id == path.id
        ).all()
        completed_names = [c.subtopic_name for c in completed]
        
        # Calculate progress
        progress = 0.0
        if subtopics:
            progress = (len(completed) / len(subtopics)) * 100
        
        paths_data.append({
            "id": path.id,
            "topic": path.topic,
            "level": path.level,
            "overview": path.overview,
            "subtopics": subtopic_names,
            "subtopics_detailed": subtopics_detailed,
            "roadmap": path.roadmap,
            "estimated_hours": path.estimated_hours,
            "progress": progress,
            "created_at": path.created_at,
            "last_updated": path.last_updated
        })
    
    return paths_data

@app.get("/api/learning-paths/{path_id}", response_model=LearningPathResponse)
async def get_learning_path(
    path_id: str, 
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    # Get the learning path
    path = db.query(LearningPath).filter(
        LearningPath.id == path_id,
        LearningPath.user_id == current_user.id
    ).first()
    
    if not path:
        raise HTTPException(status_code=404, detail="Learning path not found")
    
    # Get subtopics for this path
    subtopics = db.query(Subtopic).filter(Subtopic.learning_path_id == path_id).all()
    subtopic_names = [s.name for s in subtopics]
    subtopics_detailed = [{"name": s.name, "explanation": s.explanation} for s in subtopics]
    
    # Get completed subtopics
    completed = db.query(CompletedSubtopic).filter(
        CompletedSubtopic.learning_path_id == path_id
    ).all()
    completed_names = [c.subtopic_name for c in completed]
    
    # Calculate progress
    progress = 0.0
    if subtopics:
        progress = (len(completed) / len(subtopics)) * 100
    
    return {
        "id": path.id,
        "topic": path.topic,
        "level": path.level,
        "overview": path.overview,
        "subtopics": subtopic_names,
        "subtopics_detailed": subtopics_detailed,
        "roadmap": path.roadmap,
        "estimated_hours": path.estimated_hours,
        "progress": progress,
        "created_at": path.created_at,
        "last_updated": path.last_updated,
        "completed_subtopics": completed_names
    }

@app.put("/api/learning-paths/{path_id}/progress")
async def update_learning_path_progress(
    path_id: str,
    progress_data: dict,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    try:
        # Get the learning path
        path = db.query(LearningPath).filter(
            LearningPath.id == path_id,
            LearningPath.user_id == current_user.id
        ).first()
        
        if not path:
            raise HTTPException(status_code=404, detail="Learning path not found")
        
        # Update last_updated timestamp
        path.last_updated = datetime.utcnow()
        
        # Update progress if provided
        if "progress" in progress_data:
            path.progress = float(progress_data["progress"])
        
        # Update completed subtopics if provided
        if "completed_subtopics" in progress_data:
            # Delete existing completed subtopics
            db.query(CompletedSubtopic).filter(
                CompletedSubtopic.learning_path_id == path_id
            ).delete(synchronize_session=False)
            
            # Add new completed subtopics
            for subtopic_name in progress_data["completed_subtopics"]:
                completed = CompletedSubtopic(
                    learning_path_id=path_id,
                    subtopic_name=subtopic_name
                )
                db.add(completed)
        
        db.commit()
        
        return {"status": "success", "message": "Progress updated successfully"}
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating progress: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error updating progress: {str(e)}")

# New endpoints for resources (images, code, references, videos)
@app.post("/api/learning-paths/{path_id}/subtopics/{subtopic_id}/resources")
async def add_resource(
    path_id: str,
    subtopic_id: int,
    resource: ResourceRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    # Verify the learning path belongs to the user
    path = db.query(LearningPath).filter(
        LearningPath.id == path_id,
        LearningPath.user_id == current_user.id
    ).first()
    
    if not path:
        raise HTTPException(status_code=404, detail="Learning path not found")
    
    # Verify the subtopic belongs to the learning path
    subtopic = db.query(Subtopic).filter(
        Subtopic.id == subtopic_id,
        Subtopic.learning_path_id == path_id
    ).first()
    
    if not subtopic:
        raise HTTPException(status_code=404, detail="Subtopic not found")
    
    # Create the resource
    db_resource = Resource(
        subtopic_id=subtopic_id,
        type=resource.type,
        content=resource.content,
        title=resource.title,
        url=resource.url
    )
    
    db.add(db_resource)
    db.commit()
    db.refresh(db_resource)
    
    return {
        "id": db_resource.id,
        "type": db_resource.type,
        "content": db_resource.content,
        "title": db_resource.title,
        "url": db_resource.url
    }

@app.get("/api/learning-paths/{path_id}/subtopics/{subtopic_id}/resources")
async def get_resources(
    path_id: str,
    subtopic_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    # Verify the learning path belongs to the user
    path = db.query(LearningPath).filter(
        LearningPath.id == path_id,
        LearningPath.user_id == current_user.id
    ).first()
    
    if not path:
        raise HTTPException(status_code=404, detail="Learning path not found")
    
    # Verify the subtopic belongs to the learning path
    subtopic = db.query(Subtopic).filter(
        Subtopic.id == subtopic_id,
        Subtopic.learning_path_id == path_id
    ).first()
    
    if not subtopic:
        raise HTTPException(status_code=404, detail="Subtopic not found")
    
    # Get resources for this subtopic
    resources = db.query(Resource).filter(Resource.subtopic_id == subtopic_id).all()
    
    return [
        {
            "id": r.id,
            "type": r.type,
            "content": r.content,
            "title": r.title,
            "url": r.url
        }
        for r in resources
    ]

# Endpoint for file uploads (images, etc.)
@app.post("/api/upload")
async def upload_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user)
):
    # Create uploads directory if it doesn't exist
    uploads_dir = BASE_DIR / "static" / "uploads" / str(current_user.id)
    uploads_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate unique filename
    file_extension = file.filename.split(".")[-1]
    unique_filename = f"{uuid.uuid4()}.{file_extension}"
    file_path = uploads_dir / unique_filename
    
    # Save the file
    with open(file_path, "wb") as f:
        f.write(await file.read())
    
    # Return the URL to access the file
    file_url = f"/static/uploads/{current_user.id}/{unique_filename}"
    
    return {"url": file_url, "filename": unique_filename}

# New endpoints for searching external content
@app.get("/api/search/images")
async def search_images(
    q: str,
    current_user: User = Depends(get_current_active_user)
):
    """
    Search for images related to a query.
    Returns a list of image URLs.
    """
    try:
        # For demonstration, we'll return a few image URLs based on the query
        # In production, integrate with a proper image search API
        results = []
        
        # Generate 5 different image URLs with slight variations of the query
        base_query = q.strip()
        queries = [
            base_query,
            f"{base_query} example",
            f"{base_query} illustration",
            f"{base_query} diagram",
            f"{base_query} concept"
        ]
        
        for query_variant in queries:
            image_url = search_image(query_variant)
            if image_url:
                results.append({
                    "url": image_url,
                    "title": f"Image for {query_variant}",
                    "source": "Unsplash"
                })
        
        return {"query": q, "results": results}
    except Exception as e:
        logger.error(f"Error in image search: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error searching for images: {str(e)}")

@app.get("/api/search/videos")
async def search_videos(
    q: str,
    current_user: User = Depends(get_current_active_user)
):
    """
    Search for videos related to a query.
    Returns a list of video information including URLs.
    """
    try:
        # For demonstration, we'll return a few video URLs based on the query
        # In production, integrate with YouTube Data API or similar
        results = []
        
        # Generate variations of the query for different video results
        base_query = q.strip()
        queries = [
            base_query,
            f"{base_query} tutorial",
            f"{base_query} explained",
            f"how to {base_query}",
            f"learn {base_query}"
        ]
        
        for i, query_variant in enumerate(queries):
            video_url = search_youtube_video(query_variant)
            if video_url:
                results.append({
                    "url": video_url,
                    "title": f"{query_variant.title()}",
                    "thumbnail": f"https://img.youtube.com/vi/{video_url.split('=')[-1] if '=' in video_url else 'default'}/mqdefault.jpg",
                    "duration": f"{(i+2)*3}:{(i*13)%60:02d}",  # Fake duration for demonstration
                    "source": "YouTube"
                })
        
        return {"query": q, "results": results}
    except Exception as e:
        logger.error(f"Error in video search: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error searching for videos: {str(e)}")
    
@app.get("/api/learning-paths/{path_id}/subtopics/{subtopic_id}/detailed")
async def get_detailed_subtopic_content(
    path_id: str,
    subtopic_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get or generate detailed content for a subtopic"""
    try:
        # Verify the learning path belongs to the user
        path = db.query(LearningPath).filter(
            LearningPath.id == path_id,
            LearningPath.user_id == current_user.id
        ).first()
        
        if not path:
            raise HTTPException(status_code=404, detail="Learning path not found")
        
        # Get the subtopic
        subtopics = db.query(Subtopic).filter(
            Subtopic.learning_path_id == path_id
        ).all()
        
        if not subtopics or len(subtopics) < subtopic_id:
            raise HTTPException(status_code=404, detail="Subtopic not found")
        
        subtopic = subtopics[subtopic_id - 1]
        
        # Check if we already have a detailed explanation
        detailed_resource = db.query(Resource).filter(
            Resource.subtopic_id == subtopic.id,
            Resource.type == "detailed_explanation"
        ).first()
        
        if detailed_resource:
            # Return existing detailed explanation
            return {
                "name": subtopic.name,
                "explanation": subtopic.explanation,
                "detailed_explanation": detailed_resource.content
            }
        
        # Generate a detailed explanation
        prompt = f"""
You are an educational assistant. Provide a detailed explanation about "{subtopic.name}" as part of the broader topic "{path.topic}".

The basic explanation is: "{subtopic.explanation}"

Expand on this with a comprehensive explanation that would help someone understand this concept in depth.
Include key points, examples, and practical applications where relevant.
"""

        # Make API call to generate detailed content
        endpoint_url = "https://ai-proxy.lab.epam.com/openai/deployments/gpt-4o/chat/completions"
        
        params = {
            "api-version": "2023-12-01-preview"
        }
        
        headers = {
            "Content-Type": "application/json",
            "Api-Key": DIAL_API_KEY
        }

        data = {
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.7,
            "max_tokens": 1000
        }
        
        response = requests.post(
            endpoint_url, 
            headers=headers, 
            json=data,
            params=params,
            timeout=60
        )
        
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=response.text)
        
        detailed_explanation = response.json()["choices"][0]["message"]["content"]
        
        # Store the detailed explanation
        new_resource = Resource(
            subtopic_id=subtopic.id,
            type="detailed_explanation",
            content=detailed_explanation,
            title="Detailed Explanation"
        )
        
        db.add(new_resource)
        db.commit()
        
        return {
            "name": subtopic.name,
            "explanation": subtopic.explanation,
            "detailed_explanation": detailed_explanation
        }
        
    except Exception as e:
        logger.error(f"Error generating detailed content: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Document processing and RAG endpoints
@app.post("/submit-urls")
def submit_urls(
    payload: URLPayload,
    current_user: User = Depends(get_current_active_user)
):
    try:
        # Clear old data
        collection.delete(where={"id": {"$ne": ""}})

        splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
        all_chunks = []
        all_ids = []
        all_metadata = []

        for idx, url in enumerate(payload.urls):
            text = scrape_text_from_url(url)
            print(f"Scraped text from {url}: {text[:100]}...")  # For debugging
            if text:
                chunks = splitter.split_text(text)
                for chunk_idx, chunk in enumerate(chunks):
                    all_chunks.append(chunk)
                    all_ids.append(f"doc_{idx}_{chunk_idx}")
                    all_metadata.append({"url": url})

        if all_chunks:
            collection.add(documents=all_chunks, ids=all_ids, metadatas=all_metadata)
            return {"status": "success", "chunks_added": len(all_chunks)}
        else:
            return {"status": "error", "message": "No text extracted from provided URLs"}

    except Exception as e:
        print(f"Error in submit_urls: {e}")
        return {"status": "error", "message": str(e)}

@app.post("/ask")
def ask_question(
    payload: QuestionPayload,
    current_user: User = Depends(get_current_active_user)
):
    try:
        results = collection.query(query_texts=[payload.question], n_results=5)
        if results and results.get("documents") and results["documents"][0]:
            context = "\n".join(results["documents"][0])
            answer = query_epam_dial_llm(payload.question, context)
            return {"answer": answer}
        else:
            return {"error": "No relevant context found."}
    except Exception as e:
        print(f"Error in ask: {e}")
        return {"error": str(e)}

@app.post("/clear")
def clear_collection(
    current_user: User = Depends(get_current_active_user)
):
    try:
        collection.delete(where={"id": {"$ne": ""}})
        return {"status": "success", "message": "Collection cleared"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    
class AnswersPayload(BaseModel):
    answers: Dict[str, str]  # keys come as strings from JSON

@app.post("/generate-quiz")
def generate_quiz(
    payload: URLPayload,
    current_user: User = Depends(get_current_active_user)
):
    try:
        collection.delete(where={"id": {"$ne": ""}})
        splitter = CharacterTextSplitter(separator="\n", chunk_size=1000, chunk_overlap=100)
        all_chunks = []
        all_ids = []

        for i, url in enumerate(payload.urls):
            text = scrape_text_from_url(url)  # Using the existing function
            chunks = splitter.split_text(text)
            for j, chunk in enumerate(chunks):
                all_chunks.append(chunk)
                all_ids.append(f"doc_{i}_{j}")

        collection.add(documents=all_chunks, ids=all_ids)

        # Generate 10 questions
        context = "\n".join(all_chunks[:5])  # limit context
        prompt = f"Context:\n{context}\n\nGenerate 10 conceptual quiz questions for a student based on this content. Strictly generate questions only, no answers."
        quiz_text = query_epam_dial_llm(prompt, "")  # Using existing function

        global questions_store
        # Normalize questions from the LLM output
        questions_store = [
            q.strip("- ").strip() for q in quiz_text.strip().split("\n") if q.strip()
        ][:10]

        return {"questions": questions_store}
    except Exception as e:
        logger.error(f"Error generating quiz: {str(e)}")
        return {"error": str(e)}

@app.post("/submit-answers")
def evaluate_answers(
    payload: AnswersPayload,
    current_user: User = Depends(get_current_active_user)
):
    if not questions_store:
        return {"error": "No quiz generated yet."}

    results = []
    score = 0.0

    for key, user_answer in payload.answers.items():
        try:
            i = int(key)  # convert key to int index
        except ValueError:
            results.append({
                "question": None,
                "user_answer": user_answer,
                "score": 0,
                "feedback": "Invalid question index."
            })
            continue

        if i < 0 or i >= len(questions_store):
            results.append({
                "question": None,
                "user_answer": user_answer,
                "score": 0,
                "feedback": "Question index out of range."
            })
            continue

        question = questions_store[i]
        logger.info(f"Evaluating answer for question {i}: {user_answer}")

        prompt = f"""
Question: {question}
User Answer: {user_answer}

Evaluate the answer on a scale of 0 to 1. Respond with a JSON like: {{ "score": 0.7, "feedback": "Good but missed a detail." }}
"""
        result = query_epam_dial_llm(prompt, "")  # Using existing function

        try:
            parsed = json.loads(result)
            score_val = float(parsed.get("score", 0))
            feedback = parsed.get("feedback", "No feedback provided.")
        except Exception:
            # fallback if not JSON
            score_val = 0
            feedback = "Evaluation failed or invalid response format."

        results.append({
            "question": question,
            "user_answer": user_answer,
            "score": score_val,
            "feedback": feedback
        })
        score += score_val

    final_score = round(score, 1)
    return {
        "results": results,
        "final_score": final_score,
        "out_of": len(questions_store)
    }

if __name__ == "__main__":
    # Run the server
    import uvicorn
    print("\nStarting FastAPI server...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
