import streamlit as st
from query import * 
import argparse
import requests
from pymongo import MongoClient
import google.generativeai as genai

GEMINI_API_KEY = get_secret("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)

def build_context(docs):
    context = ""
    for i, (_, doc) in enumerate(docs, 1):
        context += f"[Doc {i}]\nGiải thích: {doc.get('explanation')}\nCode: {doc.get('code')}\nLink: {doc.get('link')}\n\n"
    return context

def ask_groq(question, context, chat_history=None, model="llama3-70b-8192"):
    '''
    Hàm gọi Groq API với chat history để duy trì cuộc hội thoại
    chat_history: list of {"role": "user/assistant", "content": "...}
    '''
    try:
        api_key = get_secret("GROQ_API_KEY")
        url = get_secret("GROQ_URL")
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        with open("prompt.txt", "r", encoding="utf-8") as f:
            system_prompt = f.read().strip()
        # Tạo messages với system prompt + chat history + context hiện tại
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
        resp = requests.post(url, headers=headers, json=payload, timeout=60)
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
        # Kết nối MongoDB
        MONGODB_URI = get_secret("MONGODB_URI")
        client = MongoClient(MONGODB_URI)
        # Chỉ định rõ tên database thay vì dùng get_default_database()
        db = client["chatcodeai"]
        collection = db["normalized"]
        # Tìm kiếm tài liệu liên quan nhất
        query = {"question": question}
        docs = collection.find(query).sort("_id", -1).limit(topk)
        docs = list(docs)
        # Nếu không tìm thấy tài liệu nào
        if not docs:
            return "Xin lỗi, tôi không tìm thấy thông tin liên quan.", "", chat_history
        # Xây dựng ngữ cảnh từ tài liệu
        context = build_context(docs)
        # Gọi Groq để lấy phản hồi
        answer = ask_groq(question, context, chat_history, model)
        # Lưu lịch sử trò chuyện
        if chat_history is None:
            chat_history = []
        chat_history.append({"role": "user", "content": question})
        chat_history.append({"role": "assistant", "content": answer})
        # Trả về câu trả lời, ngữ cảnh và lịch sử trò chuyện đã cập nhật
        return answer, context, chat_history
    except Exception as e:
        error_msg = f"Exception in get_chatbot_response: {str(e)}"
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
