from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Dict
import requests
from bs4 import BeautifulSoup
from langchain.text_splitter import CharacterTextSplitter
from chromadb import Client
from chromadb.config import Settings
from chromadb.utils import embedding_functions
from dotenv import load_dotenv
import os

load_dotenv()
DIAL_API_KEY = os.getenv("DIAL_API_KEY")
DIAL_API_URL = os.getenv("DIAL_API_URL")

app = FastAPI()

chroma_client = Client(Settings(anonymized_telemetry=False))
embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction()
collection = chroma_client.get_or_create_collection(name="quiz_collection", embedding_function=embedding_fn)

class URLPayload(BaseModel):
    urls: List[str]

class AnswersPayload(BaseModel):
    answers: Dict[int, str]  # {question_index: user_answer}

questions_store: List[str] = []  # Temporary in-memory store

def scrape_text(url: str) -> str:
    try:
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        return soup.get_text()
    except Exception as e:
        print(f"Scrape error: {e}")
        return ""

def query_llm(prompt: str) -> str:
    try:
        headers = {
            "Content-Type": "application/json",
            "Api-Key": DIAL_API_KEY
        }
        params = {
            "api-version": "2023-12-01-preview"
        }
        data = {
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.5,
            "max_tokens": 1000
        }
        res = requests.post(f"{DIAL_API_URL}/openai/deployments/gpt-4o/chat/completions",
                            headers=headers, params=params, json=data, timeout=60)
        return res.json()["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"LLM error: {e}")
        return "Error generating response"

@app.post("/generate-quiz")
def generate_quiz(payload: URLPayload):
    try:
        collection.delete(where={"id": {"$ne": ""}})
        splitter = CharacterTextSplitter(separator="\n", chunk_size=1000, chunk_overlap=100)
        all_chunks = []
        all_ids = []

        for i, url in enumerate(payload.urls):
            text = scrape_text(url)
            chunks = splitter.split_text(text)
            for j, chunk in enumerate(chunks):
                all_chunks.append(chunk)
                all_ids.append(f"doc_{i}_{j}")

        collection.add(documents=all_chunks, ids=all_ids)

        # Generate 10 questions
        context = "\n".join(all_chunks[:5])  # limit context
        prompt = f"Context:\n{context}\n\nGenerate 10 conceptual quiz questions for a student based on this content."
        quiz_text = query_llm(prompt)
        global questions_store
        questions_store = [q.strip("- ").strip() for q in quiz_text.strip().split("\n") if q.strip()]
        questions_store = questions_store[:10]
        return {"questions": questions_store}
    except Exception as e:
        return {"error": str(e)}

@app.post("/submit-answers")
def evaluate_answers(payload: AnswersPayload):
    if not questions_store:
        return {"error": "No quiz generated yet."}

    results = []
    score = 0

    for i, user_answer in payload.answers.items():
        question = questions_store[i]
        prompt = f"""
        Question: {question}
        User Answer: {user_answer}
        
        Evaluate the answer on a scale of 0 to 1. Respond with a JSON like: {{ "score": 0.7, "feedback": "Good but missed a detail." }}
        """
        result = query_llm(prompt)
        try:
            parsed = eval(result)  # Use json.loads if well-formed
            results.append({
                "question": question,
                "user_answer": user_answer,
                "score": parsed["score"],
                "feedback": parsed["feedback"]
            })
            score += parsed["score"]
        except:
            results.append({
                "question": question,
                "user_answer": user_answer,
                "score": 0,
                "feedback": "Evaluation failed."
            })

    return {
        "results": results,
        "final_score": round(score, 1),
        "out_of": 10
    }
