import os
import time
import hashlib
import requests
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from ddgs import DDGS
from bs4 import BeautifulSoup
import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions
from cachetools import TTLCache
from loguru import logger

# CONFIGURATION
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
if not OPENROUTER_API_KEY:
    raise ValueError(" Missing OPENROUTER_API_KEY environment variable!")

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "mistralai/mixtral-8x7b-instruct"

logger.info("Starting Autonomous Jarvis v5.1...")

app = FastAPI(title="🚀 AI Agent v5.1 — Web + Memory + Reflection")

# MEMORY & CACHE SETUP
cache = TTLCache(maxsize=200, ttl=3600)

# New-style Chroma initialization (fixes your migration error)
chroma_client = chromadb.Client(Settings(anonymized_telemetry=False))
embedding_fn = embedding_functions.DefaultEmbeddingFunction()

# Create persistent collection
collection_name = "long_term_memory"
if collection_name not in [c.name for c in chroma_client.list_collections()]:
    collection = chroma_client.create_collection(
        name=collection_name, embedding_function=embedding_fn
    )
else:
    collection = chroma_client.get_collection(collection_name)

# MEMORY MANAGEMENT
def save_memory(prompt, response):
    doc_id = hashlib.md5(prompt.encode()).hexdigest()
    try:
        collection.add(documents=[response], ids=[doc_id])
        logger.info(f" Memory saved for: {prompt[:40]}")
    except Exception as e:
        logger.error(f"⚠️ Memory save error: {e}")

def retrieve_memory(query):
    try:
        results = collection.query(query_texts=[query], n_results=3)
        return " ".join(results["documents"][0]) if results["documents"] else ""
    except Exception as e:
        logger.error(f"⚠️ Memory retrieval error: {e}")
        return ""

# WEB SEARCH TOOL
def web_search(query, max_results=5):
    snippets = []
    try:
        for r in DDGS().text(query, max_results=max_results):
            snippets.append(f"{r['title']}: {r['body']}")
    except Exception as e:
        logger.error(f" Search failed: {e}")
    return "\n".join(snippets) if snippets else "No web results found."

# REFLECTION LOOP
def reflection_loop(prompt, initial_response):
    reflection_prompt = f"""
Analyze and improve this response for clarity, accuracy, and completeness.
User Query: {prompt}
Previous Response: {initial_response}
Improved Version:
"""
    improved = generate_response(reflection_prompt)
    return improved if improved else initial_response

# GENERATE RESPONSE (OpenRouter)
def generate_response(prompt, context=""):
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "HTTP-Referer": "http://localhost:8000",
        "X-Title": "Jarvis AI Agent",
        "Content-Type": "application/json",
    }

    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are Jarvis — a precise, reflective AI assistant that fuses "
                    "web knowledge, past memories, and logic to deliver accurate, "
                    "well-structured answers."
                ),
            },
            {"role": "user", "content": f"{context}\n\nUser: {prompt}"},
        ],
    }

    response = requests.post(OPENROUTER_URL, headers=headers, json=payload)
    if response.status_code != 200:
        logger.error(f" OpenRouter Error: {response.text}")
        return f"Error from OpenRouter: {response.text}"

    try:
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        logger.error(f"⚠️ Parsing error: {e}")
        return "Error parsing response."

# MAIN ENDPOINT
@app.post("/ask")
async def ask(request: Request):
    start_time = time.time()
    data = await request.json()
    prompt = data.get("prompt", "").strip()

    if not prompt:
        return JSONResponse({"error": "Missing prompt."}, status_code=400)

    if prompt in cache:
        return {
            "response": cache[prompt],
            "cached": True,
            "related_memories": [],
            "processing_time": f"{round(time.time() - start_time, 2)}s",
        }

    memory_context = retrieve_memory(prompt)
    context = memory_context

    # Auto web search trigger
    if any(word in prompt.lower() for word in ["search", "find", "latest", "news", "update"]):
        query = prompt.replace("search", "").replace("find", "").strip()
        web_data = web_search(query)
        context += f"\n\n[ Web Search Results]\n{web_data}"

    # Generate response + reflect
    initial_response = generate_response(prompt, context)
    final_response = reflection_loop(prompt, initial_response)

    save_memory(prompt, final_response)
    cache[prompt] = final_response

    return {
        "response": final_response,
        "cached": False,
        "related_memories": [memory_context] if memory_context else [],
        "processing_time": f"{round(time.time() - start_time, 2)}s",
    }

# HEALTH CHECK
@app.get("/health")
def health_check():
    try:
        memory_count = len(collection.get()["ids"])
    except Exception:
        memory_count = 0
    return {"status": "healthy", "memory_items": memory_count}

# ROOT ENDPOINT
@app.get("/")
def root():
    return {
        "message": " Jarvis AI Agent running "
    }

