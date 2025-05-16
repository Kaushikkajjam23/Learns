# server.py
from fastapi import FastAPI, HTTPException, Request, Depends, status, File, UploadFile, Form, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
import secrets
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
from dotenv import load_dotenv
import os
import pathlib
import json
import logging
from datetime import timedelta, datetime
from typing import List, Optional
import uuid
from sqlalchemy.orm import Session
import pandas as pd
from docx import Document
import PyPDF2
import io
import re

# Import auth module
from auth import (
    Token, UserOut, UserCreate, authenticate_user, 
    create_access_token, get_current_active_user, create_user,
    ACCESS_TOKEN_EXPIRE_MINUTES, get_password_hash, verify_password
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

# Password reset token storage (in-memory for simplicity)
# In production, store these in a database with expiration times
password_reset_tokens = {}

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

class PasswordResetRequest(BaseModel):
    email: str

class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str

# Email sending function
def send_password_reset_email(email: str, token: str):
    try:
        # Configure your email settings here - replace with your actual email settings
        sender_email = os.getenv("EMAIL_SENDER", "your-app@example.com")
        smtp_server = os.getenv("SMTP_SERVER", "smtp.example.com")
        smtp_port = int(os.getenv("SMTP_PORT", "587"))
        smtp_username = os.getenv("SMTP_USERNAME", "your-username")
        smtp_password = os.getenv("SMTP_PASSWORD", "your-password")
        
        # Create reset link
        reset_link = f"http://localhost:3000/reset-password?token={token}"
        
        # Create email message
        message = MIMEMultipart()
        message["From"] = sender_email
        message["To"] = email
        message["Subject"] = "Password Reset Request"
        
        # Email body
        body = f"""
        <html>
        <body>
            <h2>Password Reset Request</h2>
            <p>You have requested to reset your password. Click the link below to reset it:</p>
            <p><a href="{reset_link}">Reset Password</a></p>
            <p>If you didn't request this, please ignore this email.</p>
            <p>This link will expire in 1 hour.</p>
        </body>
        </html>
        """
        
        message.attach(MIMEText(body, "html"))
        
        # Connect to SMTP server and send email
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_username, smtp_password)
            server.sendmail(sender_email, email, message.as_string())
            
        logger.info(f"Password reset email sent to {email}")
    except Exception as e:
        logger.error(f"Failed to send email to {email}: {str(e)}")
        # In production, you might want to handle this more gracefully

# Authentication routes with improved debugging
@app.post("/api/auth/login", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    try:
        logger.info(f"Login attempt for user: {form_data.username}")
        
        # Find user by email
        user = db.query(User).filter(User.email == form_data.username).first()
        
        if not user:
            logger.warning(f"User not found: {form_data.username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        logger.info(f"User found: {user.email}, verifying password...")
        
        # Verify password
        if not verify_password(form_data.password, user.hashed_password):
            logger.warning(f"Invalid password for user: {form_data.username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Create access token
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.email}, expires_delta=access_token_expires
        )
        
        logger.info(f"Login successful for user: {form_data.username}")
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user_id": user.id,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name
        }
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login error: {str(e)}",
        )

@app.post("/api/auth/register", response_model=UserOut)
async def register_new_user(user_data: UserCreate, db: Session = Depends(get_db)):
    try:
        logger.info(f"Registration attempt for email: {user_data.email}")
        return create_user(db, user_data)
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Registration failed: {str(e)}"
        )

@app.get("/api/auth/me", response_model=UserOut)
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    return current_user

# Password reset request endpoint
@app.post("/api/auth/forgot-password")
async def forgot_password(
    request: PasswordResetRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    email = request.email
    if not email:
        raise HTTPException(status_code=400, detail="Email is required")
    
    logger.info(f"Password reset requested for email: {email}")
    
    # Check if user exists
    user = db.query(User).filter(User.email == email).first()
    if not user:
        # For security reasons, don't reveal that the email doesn't exist
        logger.warning(f"Password reset requested for non-existent email: {email}")
        return {"message": "If your email is registered, you will receive a password reset link"}
    
    # Generate a secure token
    token = secrets.token_urlsafe(32)
    
    # Store token with expiration time (1 hour)
    expiration = datetime.utcnow() + timedelta(hours=1)
    password_reset_tokens[token] = {
        "user_id": user.id,
        "expiration": expiration
    }
    
    # Send email in the background
    background_tasks.add_task(send_password_reset_email, email, token)
    
    return {"message": "If your email is registered, you will receive a password reset link"}

# Reset password endpoint
@app.post("/api/auth/reset-password")
async def reset_password(
    request: PasswordResetConfirm,
    db: Session = Depends(get_db)
):
    token = request.token
    new_password = request.new_password
    
    if not token or not new_password:
        raise HTTPException(status_code=400, detail="Token and new password are required")
    
    logger.info(f"Password reset attempt with token: {token[:10]}...")
    
    # Check if token exists and is valid
    if token not in password_reset_tokens:
        logger.warning(f"Invalid password reset token: {token[:10]}...")
        raise HTTPException(status_code=400, detail="Invalid or expired token")
    
    token_data = password_reset_tokens[token]
    
    # Check if token has expired
    if datetime.utcnow() > token_data["expiration"]:
        # Remove expired token
        logger.warning(f"Expired password reset token: {token[:10]}...")
        del password_reset_tokens[token]
        raise HTTPException(status_code=400, detail="Token has expired. Please request a new password reset")
    
    # Get user
    user = db.query(User).filter(User.id == token_data["user_id"]).first()
    if not user:
        logger.error(f"User not found for token: {token[:10]}...")
        raise HTTPException(status_code=404, detail="User not found")
    
    # Update password
    hashed_password = get_password_hash(new_password)
    user.hashed_password = hashed_password
    db.commit()
    
    # Remove used token
    del password_reset_tokens[token]
    
    logger.info(f"Password reset successful for user: {user.email}")
    return {"message": "Password has been reset successfully"}

# Debugging endpoints
@app.get("/api/debug/check-db")
async def check_db(db: Session = Depends(get_db)):
    try:
        # Try to query the database
        user_count = db.query(User).count()
        return {"status": "Database connection successful", "user_count": user_count}
    except Exception as e:
        return {"status": "Database connection failed", "error": str(e)}

@app.post("/api/debug/create-test-user")
async def create_test_user(db: Session = Depends(get_db)):
    try:
        # Check if test user already exists
        test_email = "test@example.com"
        existing_user = db.query(User).filter(User.email == test_email).first()
        
        if existing_user:
            return {"status": "User already exists", "user_id": existing_user.id}
        
        # Create test user
        hashed_password = get_password_hash("testpassword")
        new_user = User(
            email=test_email,
            hashed_password=hashed_password,
            first_name="Test",
            last_name="User",
            role="user"
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        return {"status": "Test user created", "user_id": new_user.id}
    except Exception as e:
        db.rollback()
        return {"status": "Failed to create test user", "error": str(e)}

# Existing routes
@app.get("/", response_class=HTMLResponse)
async def serve_index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

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

# server.py - Update the submit_topic function to include preferences in the prompt
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

        # Rest of the function remains the same...
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

@app.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    try:
        logger.info(f"Login attempt for user: {form_data.username}")
        
        # Find user by email
        user = db.query(User).filter(User.email == form_data.username).first()
        
        if not user:
            logger.warning(f"User not found: {form_data.username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        logger.info(f"User found: {user.email}, verifying password...")
        
        # Verify password
        if not verify_password(form_data.password, user.hashed_password):
            logger.warning(f"Invalid password for user: {form_data.username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Create access token
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.email}, expires_delta=access_token_expires
        )
        
        logger.info(f"Login successful for user: {form_data.username}")
        
        # Return only the fields that exist in your User model
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user_id": user.id,
            "email": user.email
            # Remove first_name and last_name
        }
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login error: {str(e)}",
        )
    
    
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

# server.py - Update the progress endpoint
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

# server.py - Update the get_detailed_subtopic_content function

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

Format your response as a well-structured educational text with:
- Clear headings using markdown (### for headings)
- Concise paragraphs
- Bullet points for lists where appropriate
- Bold text for key terms
- Examples where helpful

Keep your response under 2500 tokens and format it for readability like a textbook.
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
            "max_tokens": 2500
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
        
        # Clean up the formatting to ensure consistent display
        # Remove excessive newlines
        detailed_explanation = re.sub(r'\n{3,}', '\n\n', detailed_explanation)
        
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
    
# Document upload and processing
@app.post("/api/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user)
):
    """Upload and process a document containing learning path topics"""
    try:
        # Check if user has manager role
        if current_user.role != "manager":
            raise HTTPException(status_code=403, detail="Only managers can upload documents")
        
        # Check file size (limit to 10MB)
        file_size = 0
        file_contents = await file.read()
        file_size = len(file_contents)
        
        if file_size > 10 * 1024 * 1024:  # 10MB
            raise HTTPException(status_code=400, detail="File too large (max 10MB)")
        
        # Reset file position
        file_like_object = io.BytesIO(file_contents)
        
        # Process file based on extension
        filename = file.filename.lower()
        extracted_data = None
        
        if filename.endswith('.xlsx') or filename.endswith('.xls'):
            extracted_data = process_excel_file(file_like_object)
        elif filename.endswith('.docx') or filename.endswith('.doc'):
            extracted_data = process_word_file(file_like_object)
        elif filename.endswith('.pdf'):
            extracted_data = process_pdf_file(file_like_object)
        else:
            raise HTTPException(status_code=400, detail="Unsupported file format")
        
        return extracted_data
        
    except Exception as e:
        logger.error(f"Error processing document: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

def process_excel_file(file_object):
    """Process Excel file to extract topics and subtopics"""
    try:
        # Read Excel file
        df = pd.read_excel(file_object)
        
        # Check if the file has the expected structure
        required_columns = ['Topic', 'Description', 'Level', 'Subtopics']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            raise ValueError(f"Excel file is missing required columns: {', '.join(missing_columns)}")
        
        # Process the data
        topics = []
        for _, row in df.iterrows():
            # Skip rows with empty topics
            if pd.isna(row['Topic']) or not row['Topic'].strip():
                continue
                
            # Extract subtopics (can be comma-separated or in separate rows)
            subtopics = []
            if not pd.isna(row['Subtopics']):
                if isinstance(row['Subtopics'], str):
                    # Split by commas or newlines
                    subtopics = [s.strip() for s in re.split(r',|\n', row['Subtopics']) if s.strip()]
                else:
                    subtopics = [str(row['Subtopics'])]
            
            # Set default values for missing fields
            description = row['Description'] if not pd.isna(row['Description']) else ""
            level = row['Level'] if not pd.isna(row['Level']) else "Intermediate"
            
            topics.append({
                'title': row['Topic'],
                'description': description,
                'level': level,
                'subtopics': subtopics
            })
        
        return {
            'source': 'excel',
            'topics': topics
        }
        
    except Exception as e:
        logger.error(f"Error processing Excel file: {str(e)}")
        raise ValueError(f"Error processing Excel file: {str(e)}")

def process_word_file(file_object):
    """Process Word file to extract topics and subtopics"""
    try:
        # Read Word file
        doc = Document(file_object)
        
        topics = []
        current_topic = None
        current_subtopics = []
        
        for para in doc.paragraphs:
            text = para.text.strip()
            if not text:
                continue
                
            # Check paragraph style to identify topics and subtopics
            if para.style.name.startswith('Heading 1') or para.style.name.startswith('Title'):
                # Save previous topic if exists
                if current_topic:
                    topics.append({
                        'title': current_topic,
                        'description': '',
                        'level': 'Intermediate',
                        'subtopics': current_subtopics
                    })
                
                # Start new topic
                current_topic = text
                current_subtopics = []
            
            elif para.style.name.startswith('Heading 2') or text.startswith('•') or text.startswith('-'):
                # This is a subtopic
                subtopic_text = text
                if text.startswith('•') or text.startswith('-'):
                    subtopic_text = text[1:].strip()
                
                current_subtopics.append(subtopic_text)
        
        # Add the last topic
        if current_topic:
            topics.append({
                'title': current_topic,
                'description': '',
                'level': 'Intermediate',
                'subtopics': current_subtopics
            })
        
        return {
            'source': 'word',
            'topics': topics
        }
        
    except Exception as e:
        logger.error(f"Error processing Word file: {str(e)}")
        raise ValueError(f"Error processing Word file: {str(e)}")

def process_pdf_file(file_object):
    """Process PDF file to extract topics and subtopics"""
    try:
        # Read PDF file
        pdf_reader = PyPDF2.PdfReader(file_object)
        
        # Extract text from all pages
        text = ""
        for page_num in range(len(pdf_reader.pages)):
            text += pdf_reader.pages[page_num].extract_text()
        
        # Simple heuristic to identify topics and subtopics
        # This is a basic implementation and might need refinement
        lines = text.split('\n')
        
        topics = []
        current_topic = None
        current_subtopics = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Heuristic: Topics are likely to be shorter and possibly in ALL CAPS or Title Case
            if len(line) < 50 and (line.isupper() or line.istitle()) and not line.endswith(':'):
                # Save previous topic if exists
                if current_topic:
                    topics.append({
                        'title': current_topic,
                        'description': '',
                        'level': 'Intermediate',
                        'subtopics': current_subtopics
                    })
                
                # Start new topic
                current_topic = line
                current_subtopics = []
            
            # Heuristic: Subtopics often start with bullets, numbers, or are indented
            elif line.startswith('•') or line.startswith('-') or re.match(r'^\d+\.', line):
                # This is a subtopic
                subtopic_text = re.sub(r'^[•\-\d\.]+\s*', '', line).strip()
                current_subtopics.append(subtopic_text)
        
        # Add the last topic
        if current_topic:
            topics.append({
                'title': current_topic,
                'description': '',
                'level': 'Intermediate',
                'subtopics': current_subtopics
            })
        
        return {
            'source': 'pdf',
            'topics': topics
        }
        
    except Exception as e:
        logger.error(f"Error processing PDF file: {str(e)}")
        raise ValueError(f"Error processing PDF file: {str(e)}")

# Create learning paths from document
@app.post("/api/documents/create-learning-paths")
async def create_learning_paths_from_document(
    data: dict,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create learning paths from extracted document data"""
    try:
        # Check if user has manager role
        if current_user.role != "manager":
            raise HTTPException(status_code=403, detail="Only managers can create learning paths")
        
        # Validate the data
        if 'topics' not in data or not data['topics']:
            raise HTTPException(status_code=400, detail="No topics provided")
        
        created_paths = []
        
        # Create learning paths for each topic
        for topic_data in data['topics']:
            # Generate a unique ID for this learning path
            path_id = str(uuid.uuid4())
            current_time = datetime.utcnow()
            
            # Generate overview and roadmap using AI
            topic = topic_data['title']
            level = topic_data['level']
            subtopics = topic_data['subtopics']
            
            # Generate overview
            overview = topic_data.get('description', '')
            if not overview:
                overview = f"Learning path for {topic} at {level} level."
            
            # Generate roadmap
            roadmap = generate_roadmap(topic, subtopics)
            
            # Estimate learning time
            estimated_hours = estimate_learning_time(topic, level, subtopics)
            
            # Create learning path in database
            db_learning_path = LearningPath(
                id=path_id,
                user_id=current_user.id,
                topic=topic,
                level=level,
                overview=overview,
                roadmap=roadmap,
                estimated_hours=estimated_hours,
                progress=0.0,
                created_at=current_time,
                last_updated=current_time,
                created_by=current_user.id,
                is_template=True  # Mark as template for assignment
            )
            
            db.add(db_learning_path)
            
            # Add subtopics to database
            for subtopic in subtopics:
                db_subtopic = Subtopic(
                    learning_path_id=path_id,
                    name=subtopic,
                    explanation=f"Subtopic of {topic}: {subtopic}"
                )
                db.add(db_subtopic)
            
            # Prepare response data
            created_paths.append({
                'id': path_id,
                'topic': topic,
                'level': level,
                'overview': overview,
                'subtopics': subtopics,
                'estimated_hours': estimated_hours
            })
        
        db.commit()
        
        return {
            'created_paths': created_paths
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating learning paths: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Get recently created paths
@app.get("/api/documents/recent-paths")
async def get_recently_created_paths(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get recently created learning paths by the current user"""
    try:
        # Check if user has manager role
        if current_user.role != "manager":
            raise HTTPException(status_code=403, detail="Only managers can access this endpoint")
        
        # Get paths created in the last 24 hours
        one_day_ago = datetime.utcnow() - timedelta(days=1)
        
        paths = db.query(LearningPath).filter(
            LearningPath.created_by == current_user.id,
            LearningPath.created_at >= one_day_ago,
            LearningPath.is_template == True
        ).all()
        
        result = []
        for path in paths:
            # Get subtopics
            subtopics = db.query(Subtopic).filter(
                Subtopic.learning_path_id == path.id
            ).all()
            
            subtopic_names = [s.name for s in subtopics]
            
            result.append({
                'id': path.id,
                'topic': path.topic,
                'level': path.level,
                'overview': path.overview,
                'subtopics': subtopic_names,
                'estimated_hours': path.estimated_hours
            })
        
        return result
        
    except Exception as e:
        logger.error(f"Error getting recent paths: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Assign learning paths to employees
@app.post("/api/documents/assign-paths")
async def assign_learning_paths(
    data: dict,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Assign learning paths to employees"""
    try:
        # Check if user has manager role
        if current_user.role != "manager":
            raise HTTPException(status_code=403, detail="Only managers can assign learning paths")
        
        # Validate the data
        if 'assignments' not in data or not data['assignments']:
            raise HTTPException(status_code=400, detail="No assignments provided")
        
        assignments = data['assignments']
        assigned_count = 0
        
        for assignment in assignments:
            path_id = assignment.get('pathId')
            employee_ids = assignment.get('employeeIds', [])
            deadline = assignment.get('deadline')
            priority = assignment.get('priority', 'Medium')
            
            if not path_id or not employee_ids:
                continue
            
            # Get the template path
            template_path = db.query(LearningPath).filter(
                LearningPath.id == path_id,
                LearningPath.is_template == True
            ).first()
            
            if not template_path:
                continue
            
            # Get the subtopics
            subtopics = db.query(Subtopic).filter(
                Subtopic.learning_path_id == path_id
            ).all()
            
            # Create a copy of the path for each employee
            for employee_id in employee_ids:
                # Verify the employee exists
                employee = db.query(User).filter(User.id == employee_id).first()
                if not employee:
                    continue
                
                # Generate a unique ID for this learning path
                new_path_id = str(uuid.uuid4())
                current_time = datetime.utcnow()
                
                # Create a copy of the learning path
                new_path = LearningPath(
                    id=new_path_id,
                    user_id=employee_id,
                    topic=template_path.topic,
                    level=template_path.level,
                    overview=template_path.overview,
                    roadmap=template_path.roadmap,
                    estimated_hours=template_path.estimated_hours,
                    progress=0.0,
                    created_at=current_time,
                    last_updated=current_time,
                    created_by=current_user.id,
                    is_template=False,
                    assigned_by=current_user.id,
                    deadline=deadline,
                    priority=priority
                )
                
                db.add(new_path)
                
                # Copy the subtopics
                for subtopic in subtopics:
                    new_subtopic = Subtopic(
                        learning_path_id=new_path_id,
                        name=subtopic.name,
                        explanation=subtopic.explanation
                    )
                    db.add(new_subtopic)
                
                assigned_count += 1
        
        db.commit()
        
        return {
            'success': True,
            'assigned_count': assigned_count
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error assigning learning paths: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Get all employees (for managers)
@app.get("/api/users/employees")
async def get_all_employees(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all employees (for managers to assign learning paths)"""
    try:
        # Check if user has manager role
        if current_user.role != "manager":
            raise HTTPException(status_code=403, detail="Only managers can access employee list")
        
        # Get all users with role 'employee'
        employees = db.query(User).filter(User.role == "employee").all()
        
        result = []
        for employee in employees:
            result.append({
                'id': employee.id,
                'name': f"{employee.first_name} {employee.last_name}",
                'email': employee.email
            })
        
        return result
        
    except Exception as e:
        logger.error(f"Error getting employees: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    
# Add this to your server.py file
@app.get("/api/test")
async def test_api():
    return {"message": "API is working!"}
# Add this to your server.py file
@app.get("/api/auth/debug", dependencies=[Depends(get_current_active_user)])
async def debug_auth():
    return {"message": "Authentication is working!"}

if __name__ == "__main__":
    # Run the server
    import uvicorn
    print("\nStarting FastAPI server...")
    uvicorn.run(app, host="0.0.0.0", port=8000)