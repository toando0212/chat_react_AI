import streamlit as st
from query import *
from functools import lru_cache
import argparse
import requests
from pymongo import MongoClient
import google.generativeai as genai
import os


def get_secret(key):
    # Ưu tiên lấy từ st.secrets (Streamlit Cloud)
    if hasattr(st, "secrets") and key in st.secrets:
        return st.secrets[key]
    # Fallback về biến môi trường (local development)
    value = os.getenv(key)
    if value is not None:
        return value
    # Nếu không có, raise exception rõ ràng
    raise RuntimeError(f"Secret '{key}' not found in st.secrets or environment variables!")


GEMINI_API_KEY = get_secret("GEMINI_API_KEY")
# Debug log GEMINI key and configure
try:
    # Log key length and prefix
    st.write(f"[DEBUG] GEMINI_API_KEY loaded ({len(GEMINI_API_KEY)} chars): {GEMINI_API_KEY[:5]}...{GEMINI_API_KEY[-5:]}")
    print(f"[DEBUG] GEMINI_API_KEY: {GEMINI_API_KEY}")
    genai.configure(api_key=GEMINI_API_KEY)
    st.write("[DEBUG] genai.configure succeeded")
    print("[DEBUG] genai.configure succeeded")
except Exception as e:
    st.error(f"[DEBUG] genai.configure error: {e}")
    print(f"[DEBUG] genai.configure error: {e}")
    raise

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
        st.write("✅ Đã kết nối MongoDB thành công")
        print("✅ Đã kết nối MongoDB thành công")
        return client
    except Exception as e:
        st.error(f"❌ Lỗi kết nối MongoDB: {e}")
        print(f"❌ Lỗi kết nối MongoDB: {e}")
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

def ask_groq(question, context, chat_history=None, model="llama3-70b-8192"):
    '''
    Hàm gọi Groq API với chat history để duy trì cuộc hội thoại
    chat_history: list of {"role": "user/assistant", "content": "...}
    '''
    try:
        # Load and debug log GROQ credentials
        api_key = get_secret("GROQ_API_KEY")
        url = get_secret("GROQ_URL")
        # Debug log API key and URL
        st.write(f"[DEBUG] GROQ_API_KEY loaded ({len(api_key)} chars): {api_key[:5]}...{api_key[-5:]}")
        print(f"[DEBUG] GROQ_API_KEY: {api_key}")
        st.write(f"[DEBUG] GROQ_URL: {url}")
        print(f"[DEBUG] GROQ_URL: {url}")
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        # Debug log headers (masked)
        st.write(f"[DEBUG] Request headers: Authorization=Bearer {'*' * 5}{api_key[-5:]} ...")
        print(f"[DEBUG] Request to {url} with headers {headers}")
        # Load system prompt
        with open("prompt.txt", "r", encoding="utf-8") as f:
            system_prompt = f.read().strip()
        # Create messages with system prompt + chat history + context
        messages = [{"role": "system", "content": system_prompt}]
        if chat_history:
            messages.extend(chat_history)
        current_message = f"Context:\n{context}\n\nQuestion: {question}"
        messages.append({"role": "user", "content": current_message})
        payload = {
            "model": model,
            "messages": messages,
            "temperature": 0.2,
            "max_tokens": 1024
        }
        # Send request and debug response status
        resp = requests.post(url, headers=headers, json=payload, timeout=60)
        st.write(f"[DEBUG] GROQ response status: {resp.status_code}")
        print(f"[DEBUG] GROQ response status: {resp.status_code}, body: {resp.text}")
        if resp.status_code == 200:
            return resp.json()["choices"][0]["message"]["content"]
        else:
            error_msg = f"Groq API error: {resp.status_code} {resp.text}"
            print(error_msg)
            return f"❌ Lỗi API: {error_msg}"
    except Exception as e:
        error_msg = f"Exception in ask_groq: {str(e)}"
        print(error_msg)
        return f"❌ Lỗi hệ thống: {error_msg}"

def get_chatbot_response(question, chat_history=None, topk=5, model="llama3-70b-8192"):
    '''
    Hàm chính để lấy phản hồi từ chatbot với chat history
    Returns: (answer, context_info, updated_chat_history)
    '''
    try:
        # Dùng MongoDB client đã cache
        st.write("[DEBUG] Đang lấy MongoDB client...")
        print("[DEBUG] Đang lấy MongoDB client...")
        client = get_mongodb_client()
        st.write("[DEBUG] Đã lấy được client, truy cập DB...")
        print("[DEBUG] Đã lấy được client, truy cập DB...")
        db = client["chatcodeai"]
        collection = db["normalized"]

        # Tìm kiếm tài liệu liên quan nhất bằng vector embedding (có cache)
        query_emb = get_embedding_cached(question)
        query_emb = resize_embedding(query_emb, 1024)
        docs = find_top_k(query_emb, collection, k=topk)

        # Nếu không tìm thấy tài liệu nào
        if not docs:
            st.warning("[DEBUG] Không tìm thấy tài liệu liên quan.")
            print("[DEBUG] Không tìm thấy tài liệu liên quan.")
            return "Xin lỗi, tôi không tìm thấy thông tin liên quan.", "", chat_history
        # Xây dựng ngữ cảnh từ tài liệu - docs là list các dict
        context = build_context(docs)
        # Gọi Groq để lấy phản hồi
        answer = ask_groq(question, context, chat_history, model)
        # Lưu lịch sử trò chuyện
        if chat_history is None:
            chat_history = []
        chat_history.append({"role": "user", "content": question})
        chat_history.append({"role": "assistant", "content": answer})
        # Trả về câu trả lời, ngữ cảnh và lịch sử trò chuyện đã cập nhật
        st.write("[DEBUG] Trả về kết quả thành công.")
        print("[DEBUG] Trả về kết quả thành công.")
        return answer, context, chat_history
    except Exception as e:
        error_msg = f"Exception in get_chatbot_response: {str(e)}"
        st.error(error_msg)
        print(error_msg)
        return f"❌ Lỗi hệ thống: {error_msg}", "", chat_history

def main():
    parser = argparse.ArgumentParser(description="Chatbot embedding + Groq")
    parser.add_argument('--question', type=str, help='Câu hỏi đầu vào')
    parser.add_argument('--topk', type=int, default=5, help='Số lượng context top K')
    parser.add_argument('--model', type=str, default="llama3-70b-8192", help='Model Groq (llama3-70b-8192, mixtral-8x7b-32768,...)')
    args = parser.parse_args()

    chat_history = []
    
    if args.question:
        # Single question mode
        answer, context_info, _ = get_chatbot_response(args.question, chat_history, args.topk, args.model)
        print(f"\n=== Câu hỏi ===\n{args.question}")
        print(f"\n=== Trả lời từ Groq ===\n{answer}")
        print(f"\n=== Context được sử dụng ===\n{context_info}")
    else:
        # Interactive chat mode
        print("🤖 Chào bạn! Tôi là chatbot ReactJS. Gõ 'quit' để thoát.")
        while True:
            question = input("\n👤 Bạn: ").strip()
            if question.lower() in ['quit', 'exit', 'q']:
                print("👋 Tạm biệt!")
                break
            if not question:
                continue
                
            print("🔍 Đang tìm kiếm và xử lý...")
            answer, context_info, chat_history = get_chatbot_response(question, chat_history, args.topk, args.model)
            print(f"\n🤖 Bot: {answer}")
            
            # Debug info
            print(f"\n📊 Debug - Chat history length: {len(chat_history)} messages")
            print(f"📋 Context info: {len(context_info)} characters")

if __name__ == "__main__":
    main()
