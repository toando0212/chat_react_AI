from query import * 
import argparse
import requests
from pymongo import MongoClient
import google.generativeai as genai
GEMINI_API_KEY = read_env_key("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)

def build_context(docs):
    context = ""
    for i, (_, doc) in enumerate(docs, 1):
        context += f"[Doc {i}]\nGiải thích: {doc.get('explanation')}\nCode: {doc.get('code')}\nLink: {doc.get('link')}\n\n"
    return context

def ask_groq(question, context, model="llama3-70b-8192"):
    api_key = read_env_key("GROQ_API_KEY")
    url = read_env_key("GROQ_URL")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    with open("prompt.txt", "r", encoding="utf-8") as f:
        system_prompt = f.read().strip()
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}"}
    ]
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
        print(f"Groq API error: {resp.status_code} {resp.text}")
        return None

def main():
    parser = argparse.ArgumentParser(description="Chatbot embedding + Groq")
    parser.add_argument('--question', type=str, help='Câu hỏi đầu vào')
    parser.add_argument('--topk', type=int, default=5, help='Số lượng context top K')
    parser.add_argument('--model', type=str, default="llama3-70b-8192", help='Model Groq (llama3-70b-8192, mixtral-8x7b-32768,...)')
    args = parser.parse_args()

    MONGODB_URI = read_env_key("MONGODB_URI")
    client = MongoClient(MONGODB_URI)
    db = client.get_default_database()
    collection = db["normalized"]

    if args.question:
        question = args.question
    else:
        question = input("Nhập câu hỏi của bạn: ")
    query_emb = get_embedding(question)
    query_emb = resize_embedding(query_emb, 1024)

    results = find_top_k(query_emb, collection, k=args.topk)
    print(f"\nTop {args.topk} context gần nhất:")
    for i, (score, doc) in enumerate(results, 1):
        print(f"\n--- Context #{i} (similarity={score:.3f}) ---")
        print(f"Giải thích: {doc.get('explanation')}\nCode: {doc.get('code')}\nLink: {doc.get('link')}")

    context = build_context(results)
    print("\nĐang gửi lên Groq...")
    answer = ask_groq(question, context, model=args.model)
    print("\n=== Trả lời từ Groq ===\n")
    print(answer)

if __name__ == "__main__":
    main()
