import google.generativeai as genai
from pymongo import MongoClient
import numpy as np
import os
import json
import argparse

import toml

# Ưu tiên st.secrets (Streamlit Cloud), sau đó đến biến môi trường, rồi file .env/.toml
try:
    import streamlit as st
    def get_secret(key):
        # 1. Ưu tiên lấy từ st.secrets nếu có
        try:
            import streamlit as st
            if hasattr(st, "secrets") and key in st.secrets:
                return st.secrets[key]
        except Exception:
            pass

        # 2. Nếu không có, lấy từ biến môi trường
        value = os.environ.get(key)
        if value:
            return value

        # 3. Nếu vẫn không có, thử đọc từ file .env
        try:
            from dotenv import load_dotenv
            load_dotenv()
            value = os.environ.get(key)
            if value:
                return value
        except Exception:
            pass

        # 4. Nếu vẫn không có, trả về None
        return None
except ImportError:
    def get_secret(key, env_file="key.env", toml_file="streamlit.toml"):
        # 1. Biến môi trường
        if key in os.environ:
            return os.environ[key]
        # 2. Đọc từ streamlit.toml nếu có
        try:
            config = toml.load(toml_file)
            secrets = config.get("secrets", {})
            if key in secrets:
                return secrets[key]
        except Exception:
            pass
        # 3. Đọc từ file .env local nếu có
        try:
            with open(env_file, "r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith(f"{key}="):
                        return line.strip().split("=", 1)[1]
        except FileNotFoundError:
            pass
        return None

def get_embedding(text, model="models/embedding-001"):
    response = genai.embed_content(model=model, content=[text])
    if isinstance(response, dict) and 'embedding' in response:
        embedding = response['embedding']
    elif isinstance(response, list) and len(response) > 0:
        if isinstance(response[0], dict) and 'embedding' in response[0]:
            embedding = response[0]['embedding']
        else:
            embedding = response[0]
    else:
        raise ValueError(f"Unrecognized response structure from Gemini: {response}")
    while isinstance(embedding, list) and len(embedding) > 0 and isinstance(embedding[0], list):
        embedding = embedding[0]
    flat = [float(x) if isinstance(x, (int, float)) else 0.0 for x in embedding]
    if len(flat) == 3072:
        half = len(flat) // 2
        flat = [(flat[i] + flat[i + half]) / 2 for i in range(half)]
    return flat

def resize_embedding(embedding, target_dim=1024):
    current_dim = len(embedding)
    if current_dim == target_dim:
        return embedding
    if current_dim < target_dim:
        return embedding + [0.0] * (target_dim - current_dim)
    else:
        return embedding[:target_dim]

# Hàm mới dùng Vector Search
def find_top_k(query_embedding, collection, k=8):
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
        results = list(collection.aggregate(pipeline))
        return results
    except Exception as e:
        print(f"❌ Lỗi khi tìm kiếm: {str(e)}")
        return []

def main():
    parser = argparse.ArgumentParser(description="Query chatbot with embedding search")
    parser.add_argument('--question', type=str, help='Câu hỏi đầu vào')
    args = parser.parse_args()

    # Cấu hình Gemini
    GEMINI_API_KEY = get_secret("GEMINI_API_KEY")
    if not GEMINI_API_KEY:
        print("❌ Không tìm thấy GEMINI_API_KEY")
        return
    genai.configure(api_key=GEMINI_API_KEY)
    
    # Kết nối MongoDB
    MONGODB_URI = get_secret("MONGODB_URI")
    if not MONGODB_URI:
        print("❌ Không tìm thấy MONGODB_URI")
        return
    
    client = MongoClient(MONGODB_URI)
    db = client.get_default_database()
    collection = db["normalized"]
    
    # Nhập câu hỏi
    if args.question:
        query = args.question
    else:
        query = input("Nhập câu hỏi của bạn: ")
    
    print("🔄 Đang tạo embedding...")
    query_emb = get_embedding(query)
    query_emb = resize_embedding(query_emb, 1024)

    print("🔍 Đang tìm kiếm...")
    # Tìm top 8 kết quả gần nhất
    results = find_top_k(query_emb, collection, k=8)
    print("\nTop 8 kết quả gần nhất:")
    for i, doc in enumerate(results, 1):
        print(f"\n--- Kết quả #{i} ---")
        print(f"Giải thích: {doc.get('explanation')}")
        print(f"Code: {doc.get('code')}")
        print(f"Link: {doc.get('link')}")
        print(f"Loại: {doc.get('type', 'N/A')}")
        print(f"Điểm: {doc.get('score', 0):.4f}")  # Hiển thị điểm tương đồng

if __name__ == "__main__":
    main()
