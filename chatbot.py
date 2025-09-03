import re
import os
import asyncio
import importlib.util
from functools import lru_cache
from dotenv import load_dotenv
from pymongo import MongoClient
import motor.motor_asyncio
import google.generativeai as genai
from query import *
import streamlit as st

# Load environment variables
load_dotenv()

def get_secret(key):
    """Retrieve secrets from environment variables or Streamlit secrets."""
    value = os.getenv(key)
    if value:
        return value
    try:
        if hasattr(st, "secrets") and key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass
    raise RuntimeError(f"Secret '{key}' not found in environment variables or st.secrets!")

# Configure Gemini API
genai.configure(api_key=get_secret("GEMINI_API_KEY"))

# MongoDB client management
_mongodb_client = None

async def get_mongodb_client():
    """Initialize and return a MongoDB client."""
    global _mongodb_client
    if _mongodb_client is None:
        try:
            _mongodb_client = motor.motor_asyncio.AsyncIOMotorClient(
                get_secret("MONGODB_URI"),
                maxPoolSize=10,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=5000,
                socketTimeoutMS=5000
            )
            await _mongodb_client.server_info()
        except Exception as e:
            st.error(f"❌ MongoDB connection error: {e}")
            raise
    return _mongodb_client

@lru_cache(maxsize=1000)
def get_embedding_cached(text):
    """Cache embeddings for faster retrieval."""
    return get_embedding(text)

def build_context(docs):
    """Construct context from retrieved documents."""
    return "\n".join(
        f"[Doc {i}]\nExplanation: {doc.get('explanation')}\nCode: {doc.get('code')}\nLink: {doc.get('link')}\n"
        for i, doc in enumerate(docs, 1)
    )

async def ask_cerebras(question, context, chat_history=None, model="llama-4-scout-17b-16e-instruct"):
    """Call Cerebras API with chat history."""
    try:
        spec = importlib.util.find_spec("cerebras.cloud.sdk")
        if spec is None:
            raise ImportError("Install cerebras-cloud-sdk: pip install cerebras-cloud-sdk")
        from cerebras.cloud.sdk import Cerebras
    except ImportError as e:
        return f"❌ Error: {e}"

    api_key = get_secret("CEREBRAS_API_KEY")
    with open("prompt.txt", "r", encoding="utf-8") as f:
        system_prompt = f.read().strip()

    messages = [{"role": "system", "content": system_prompt}]
    if chat_history:
        messages.extend(chat_history)
    messages.append({"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}"})

    try:
        client = Cerebras(api_key=api_key)
        response = client.chat.completions.create(
            messages=messages,
            model=model,
            temperature=0.2,
            max_tokens=2048
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"❌ Cerebras API error: {e}"

async def get_chatbot_response(question, chat_history=None, topk=5, model="gpt-oss-120b"):
    """Main function to get chatbot response."""
    client = await get_mongodb_client()
    collection = client["chatcodeai"]["normalized"]

    chat_history = chat_history or []
    query_emb = resize_embedding(get_embedding_cached(question), 1024)
    docs = await find_top_k(query_emb, collection, k=topk)

    if not docs:
        return "Sorry, no relevant information found.", "", chat_history

    context = build_context(docs)
    answer = await ask_cerebras(question, context, chat_history, model)

    chat_history.extend([
        {"role": "user", "content": question},
        {"role": "assistant", "content": answer}
    ])
    return answer, context, chat_history

async def main():
    """Entry point for chatbot interaction."""
    import argparse
    parser = argparse.ArgumentParser(description="Chatbot embedding + Cerebras")
    parser.add_argument('--question', type=str, help='Input question')
    args = parser.parse_args()

    chat_history = []

    if args.question:
        answer, _, _ = await get_chatbot_response(args.question, chat_history)
        print(remove_think_tags(answer))
    else:
        print("🤖 Hello! Type 'quit' to exit.")
        while True:
            question = input("\n👤 You: ").strip()
            if question.lower() in ['quit', 'exit', 'q']:
                print("👋 Goodbye!")
                break
            if not question:
                continue

            print("🔍 Processing...")
            answer, _, chat_history = await get_chatbot_response(question, chat_history)
            print(f"\n🤖 Bot: {remove_think_tags(answer)}")

def remove_think_tags(text):
    """Remove reasoning trace or <think> tags from the response."""
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()

if __name__ == "__main__":
    asyncio.run(main())
