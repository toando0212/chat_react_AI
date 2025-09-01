import re
# Loại bỏ reasoning trace/thẻ <think> khỏi phản hồi
def remove_think_tags(text):
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
import streamlit as st
from query import *
from functools import lru_cache
import argparse
import requests
import importlib.util
from pymongo import MongoClient
import google.generativeai as genai

import os
from dotenv import load_dotenv
load_dotenv()


def get_secret(key):
    # Ưu tiên lấy từ biến môi trường (local .env)
    value = os.getenv(key)
    if value is not None:
        return value
    # Nếu không có, thử lấy từ st.secrets (Streamlit Cloud)
    try:
        if hasattr(st, "secrets") and key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass
    # Nếu không có, raise exception rõ ràng
    raise RuntimeError(f"Secret '{key}' not found in environment variables or st.secrets!")


GEMINI_API_KEY = get_secret("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)

# Cache MongoDB client globally (Streamlit Cloud safe)
@st.cache_resource
def get_mongodb_client():
    MONGODB_URI = get_secret("MONGODB_URI")
    try:
        client = MongoClient(
            MONGODB_URI,
            maxPoolSize=10,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=5000,
            socketTimeoutMS=5000
        )
        # Try a quick server_info to force connection
        client.server_info()
        return client
    except Exception as e:
        st.error(f"❌ Lỗi kết nối MongoDB: {e}")
        raise

# Optionally cache embedding generation
@lru_cache(maxsize=1000)
def get_embedding_cached(text):
    return get_embedding(text)

def build_context(docs):
    context = ""
    for i, doc in enumerate(docs, 1):
        context += f"[Doc {i}]\nGiải thích: {doc.get('explanation')}\nCode: {doc.get('code')}\nLink: {doc.get('link')}\n\n"
    return context


# Hàm gọi Cerebras API với chat history để duy trì cuộc hội thoại
def ask_cerebras(question, context, chat_history=None, model="llama-4-scout-17b-16e-instruct"):
    '''
    Hàm gọi Cerebras API với chat history để duy trì cuộc hội thoại
    chat_history: list of {"role": "user/assistant", "content": "..."}
    '''
    # Import cerebras lib nếu có, nếu không báo lỗi rõ ràng
    try:
        spec = importlib.util.find_spec("cerebras.cloud.sdk")
        if spec is None:
            raise ImportError("Bạn cần cài đặt thư viện cerebras-cloud-sdk: pip install cerebras-cloud-sdk")
        from cerebras.cloud.sdk import Cerebras
    except ImportError as e:
        return f"❌ Lỗi: {e}"

    api_key = get_secret("CEREBRAS_API_KEY")
    # Load system prompt
    with open("prompt.txt", "r", encoding="utf-8") as f:
        system_prompt = f.read().strip()
    # Tạo messages với system prompt + chat history + context
    messages = [{"role": "system", "content": system_prompt}]
    if chat_history:
        messages.extend(chat_history)
    current_message = f"Context:\n{context}\n\nQuestion: {question}"
    messages.append({"role": "user", "content": current_message})
    try:
        client = Cerebras(api_key=api_key)
        response = client.chat.completions.create(
            messages=messages,
            model=model,
            temperature=0.2,
            max_tokens=1024
        )
        # Trả về nội dung trả lời
        return response.choices[0].message.content
    except Exception as e:
        return f"❌ Lỗi gọi Cerebras API: {e}"

def get_chatbot_response(question, chat_history=None, topk=5, model="gpt-oss-120b"):
    '''
    Hàm chính để lấy phản hồi từ chatbot với chat history
    Returns: (answer, context_info, updated_chat_history)
    '''
    # Dùng MongoDB client đã cache
    client = get_mongodb_client()
    db = client["chatcodeai"]
    collection = db["normalized"]

    # Tìm kiếm tài liệu liên quan nhất bằng vector embedding (có cache)
    query_emb = get_embedding_cached(question)
    query_emb = resize_embedding(query_emb, 1024)
    docs = find_top_k(query_emb, collection, k=topk)

    # Nếu không tìm thấy tài liệu nào
    if not docs:
        return "Xin lỗi, tôi không tìm thấy thông tin liên quan.", "", chat_history
    # Xây dựng ngữ cảnh từ tài liệu - docs là list các dict
    context = build_context(docs)
    # Gọi Cerebras để lấy phản hồi
    answer = ask_cerebras(question, context, chat_history, model)
    # Lưu lịch sử trò chuyện
    if chat_history is None:
        chat_history = []
    chat_history.append({"role": "user", "content": question})
    chat_history.append({"role": "assistant", "content": answer})
    # Trả về câu trả lời, ngữ cảnh và lịch sử trò chuyện đã cập nhật
    return answer, context, chat_history

def main():
    parser = argparse.ArgumentParser(description="Chatbot embedding + Cerebras")
    parser.add_argument('--question', type=str, help='Câu hỏi đầu vào')
    args = parser.parse_args()

    chat_history = []

    if args.question:
        # Single question mode
        answer, context_info, _ = get_chatbot_response(args.question, chat_history)
        answer = remove_think_tags(answer)
        print(answer)
    else:
        # Interactive chat mode
        print("🤖 Chào bạn! Tôi là chatbot ReactJS (Cerebras). Gõ 'quit' để thoát.")
        while True:
            question = input("\n👤 Bạn: ").strip()
            if question.lower() in ['quit', 'exit', 'q']:
                print("👋 Tạm biệt!")
                break
            if not question:
                continue

            print("🔍 Đang tìm kiếm và xử lý...")
            answer, context_info, chat_history = get_chatbot_response(question, chat_history, args.topk, args.model)
            answer = remove_think_tags(answer)
            print(f"\n🤖 Bot: {answer}")

if __name__ == "__main__":
    main()
