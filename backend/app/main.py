from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
from dotenv import load_dotenv
import os

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

# Create a Jinja2Templates instance
templates = Jinja2Templates(directory="templates")

class TopicRequest(BaseModel):
    topic: str
    level: str

@app.get("/", response_class=HTMLResponse)
async def serve_index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/api/topics")
async def submit_topic(request: TopicRequest):
    try:
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
"""

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
        for line in subtopics_block.split("\n"):
            if line.strip() and line[0].isdigit():  # Check for numbered subtopics
                subtopic_titles.append(line[line.index(".") + 1:].strip().split(":")[0].strip())

        # Generate a roadmap
        roadmap = generate_roadmap(request.topic, subtopic_titles)

        return {
            "overview": overview_match,
            "subtopics": subtopic_titles,
            "roadmap": roadmap,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

