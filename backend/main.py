from fastapi import FastAPI
from pydantic import BaseModel
from typing import List
import requests
from bs4 import BeautifulSoup
from langchain.text_splitter import RecursiveCharacterTextSplitter
from chromadb import Client
from chromadb.config import Settings
from chromadb.utils import embedding_functions
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()
DIAL_API_KEY = os.getenv("DIAL_API_KEY")
DIAL_API_URL = os.getenv("DIAL_API_URL")

# Initialize FastAPI
app = FastAPI()

# Initialize ChromaDB client with persistence
chroma_client = Client(Settings(
    anonymized_telemetry=False,
    is_persistent=True,
    persist_directory="chroma_store"
))

# Set up sentence transformer embedding
sentence_transformer_ef = embedding_functions.SentenceTransformerEmbeddingFunction()

# Create or get collection
collection = chroma_client.get_or_create_collection(
    name="my_collection",
    embedding_function=sentence_transformer_ef
)

class URLPayload(BaseModel):
    urls: List[str]

class QuestionPayload(BaseModel):
    question: str

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

@app.post("/submit-urls")
def submit_urls(payload: URLPayload):
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
def ask_question(payload: QuestionPayload):
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
def clear_collection():
    try:
        collection.delete(where={"id": {"$ne": ""}})
        return {"status": "success", "message": "Collection cleared"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
