import os
import json
import argparse
import toml
import numpy as np
from pymongo import MongoClient
import google.generativeai as genai
import motor.motor_asyncio

# Secret management
def get_secret(key, env_file="key.env", toml_file="streamlit.toml"):
    """Retrieve secrets from environment variables, .env, or .toml files."""
    if key in os.environ:
        return os.environ[key]
    try:
        config = toml.load(toml_file)
        if key in config.get("secrets", {}):
            return config["secrets"][key]
    except Exception:
        pass
    try:
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith(f"{key}="):
                    return line.strip().split("=", 1)[1]
    except FileNotFoundError:
        pass
    return None

# Embedding utilities
def get_embedding(text, model="models/embedding-001"):
    """Generate embeddings using Gemini API."""
    response = genai.embed_content(model=model, content=[text])
    embedding = response.get('embedding') or response[0].get('embedding')
    if isinstance(embedding, list) and len(embedding) > 0 and isinstance(embedding[0], list):
        embedding = embedding[0]
    flat = [float(x) if isinstance(x, (int, float)) else 0.0 for x in embedding]
    if len(flat) == 3072:
        half = len(flat) // 2
        flat = [(flat[i] + flat[i + half]) / 2 for i in range(half)]
    return flat

def resize_embedding(embedding, target_dim=1024):
    """Resize embeddings to the target dimension."""
    current_dim = len(embedding)
    if current_dim == target_dim:
        return embedding
    return embedding + [0.0] * (target_dim - current_dim) if current_dim < target_dim else embedding[:target_dim]

# Vector search
async def find_top_k(query_embedding, collection, k=8):
    """Find top-k documents using vector search asynchronously."""
    pipeline = [
        {
            "$vectorSearch": {
                "index": "vector_index",
                "path": "embedding",
                "queryVector": query_embedding,
                "numCandidates": 100,
                "limit": k
            }
        },
        {
            "$project": {
                "_id": 0,
                "type": 1,
                "explanation": 1,
                "code": 1,
                "link": 1,
                "score": {"$meta": "vectorSearchScore"}
            }
        }
    ]
    try:
        cursor = collection.aggregate(pipeline)
        if hasattr(cursor, 'to_list'):
            return await cursor.to_list(length=k)
        return list(cursor)
    except Exception as e:
        print(f"❌ Search error: {e}")
        return []

async def main():
    """Main entry point for querying chatbot."""
    parser = argparse.ArgumentParser(description="Query chatbot with embedding search")
    parser.add_argument('--question', type=str, help='Input question')
    args = parser.parse_args()

    genai.configure(api_key=get_secret("GEMINI_API_KEY"))
    client = MongoClient(get_secret("MONGODB_URI"))
    collection = client.get_default_database()["normalized"]

    query = args.question or input("Enter your question: ")
    query_emb = resize_embedding(get_embedding(query), 1024)

    print("🔍 Searching...")
    results = await find_top_k(query_emb, collection, k=8)
    for i, doc in enumerate(results, 1):
        print(f"\n--- Result #{i} ---")
        print(f"Explanation: {doc.get('explanation')}")
        print(f"Code: {doc.get('code')}")
        print(f"Link: {doc.get('link')}")
        print(f"Type: {doc.get('type', 'N/A')}")
        print(f"Score: {doc.get('score', 0):.4f}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
