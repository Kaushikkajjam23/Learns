# database.py
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, ForeignKey, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import os

# Create database directory if it doesn't exist
os.makedirs("./db", exist_ok=True)

# Create SQLite engine
SQLALCHEMY_DATABASE_URL = "sqlite:///./db/learning_paths.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class for models
Base = declarative_base()

# Define User model
# In your database.py or models.py file
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    first_name = Column(String, nullable=True)  # Add this field
    last_name = Column(String, nullable=True)   # Add this field
    role = Column(String, default="user")
    is_active = Column(Boolean, default=True)
# Define LearningPath model

class LearningPath(Base):
    __tablename__ = "learning_paths"
    
    id = Column(String, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    topic = Column(String)
    level = Column(String)
    overview = Column(Text)
    roadmap = Column(Text)
    estimated_hours = Column(Float)
    progress = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_updated = Column(DateTime, default=datetime.utcnow)
    
    # Relationship with user
    user = relationship("User", back_populates="learning_paths")
    
    # Relationship with subtopics
    subtopics = relationship("Subtopic", back_populates="learning_path", cascade="all, delete-orphan")
    
    # Relationship with completed subtopics
    completed_subtopics = relationship("CompletedSubtopic", back_populates="learning_path", cascade="all, delete-orphan")

# Define Subtopic model
class Subtopic(Base):
    __tablename__ = "subtopics"
    
    id = Column(Integer, primary_key=True, index=True)
    learning_path_id = Column(String, ForeignKey("learning_paths.id"))
    name = Column(String)
    explanation = Column(Text)
    
    # Relationship with learning path
    learning_path = relationship("LearningPath", back_populates="subtopics")
    
    # Relationship with resources
    resources = relationship("Resource", back_populates="subtopic", cascade="all, delete-orphan")

# Define CompletedSubtopic model
class CompletedSubtopic(Base):
    __tablename__ = "completed_subtopics"
    
    id = Column(Integer, primary_key=True, index=True)
    learning_path_id = Column(String, ForeignKey("learning_paths.id"))
    subtopic_name = Column(String)
    
    # Relationship with learning path
    learning_path = relationship("LearningPath", back_populates="completed_subtopics")

# Define Resource model for additional content (images, code, references, videos)
class Resource(Base):
    __tablename__ = "resources"
    
    id = Column(Integer, primary_key=True, index=True)
    subtopic_id = Column(Integer, ForeignKey("subtopics.id"))
    type = Column(String)  # "image", "code", "reference", "video"
    content = Column(Text)
    title = Column(String, nullable=True)
    url = Column(String, nullable=True)
    
    # Relationship with subtopic
    subtopic = relationship("Subtopic", back_populates="resources")

# Create all tables
Base.metadata.create_all(bind=engine)

# Function to get database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()