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
        return st.secrets.get(key) or os.environ.get(key)
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

def cosine_similarity(a, b):
    a = np.array(a)
    b = np.array(b)
    if np.linalg.norm(a) == 0 or np.linalg.norm(b) == 0:
        return 0.0
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))

def find_top_k(query_embedding, collection, k=10, ratio_stackoverflow=0.7, min_score=0.5):
    # Lấy top k từ mỗi type theo tỉ lệ
    k_so = max(1, int(k * ratio_stackoverflow))
    k_re = max(1, k - k_so)
    # StackOverflow
    docs_so = list(collection.find({"type": "stackoverflow"}, {"type": 1, "embedding": 1, "explanation": 1, "code": 1, "link": 1, "_id": 0}))
    scored_so = []
    for doc in docs_so:
        emb = doc.get("embedding")
        if not emb:
            continue
        score = cosine_similarity(query_embedding, emb)
        if score >= min_score:
            scored_so.append((score, doc))
    scored_so.sort(reverse=True, key=lambda x: x[0])
    # React Example
    docs_re = list(collection.find({"type": "react_example"}, {"type": 1, "embedding": 1, "explanation": 1, "code": 1, "link": 1, "_id": 0}))
    scored_re = []
    for doc in docs_re:
        emb = doc.get("embedding")
        if not emb:
            continue
        score = cosine_similarity(query_embedding, emb)
        if score >= min_score:
            scored_re.append((score, doc))
    scored_re.sort(reverse=True, key=lambda x: x[0])
    # Lấy top k mỗi loại
    top_so = scored_so[:k_so]
    top_re = scored_re[:k_re]
    # Gộp lại và sort lại theo similarity
    merged = top_so + top_re
    merged.sort(reverse=True, key=lambda x: x[0])
    return merged[:k]

def main():
    parser = argparse.ArgumentParser(description="Query chatbot with embedding search")
    parser.add_argument('--question', type=str, help='Câu hỏi đầu vào')
    args = parser.parse_args()

    # Cấu hình Gemini
    GEMINI_API_KEY = get_secret("GEMINI_API_KEY")
    genai.configure(api_key=GEMINI_API_KEY)
    # Kết nối MongoDB
    MONGODB_URI = get_secret("MONGODB_URI")
    client = MongoClient(MONGODB_URI)
    db = client.get_default_database()
    collection = db["normalized"]
    
    # Nhập câu hỏi
    if args.question:
        query = args.question
    else:
        query = input("Nhập câu hỏi của bạn: ")
    query_emb = get_embedding(query)
    query_emb = resize_embedding(query_emb, 1024)

    # Tìm top 10 kết quả gần nhất
    results = find_top_k(query_emb, collection, k=8)
    print("\nTop 10 kết quả gần nhất:")
    for i, (score, doc) in enumerate(results, 1):
        print(f"\n--- Kết quả #{i} (similarity={score:.3f}) ---")
        print(f"Giải thích: {doc.get('explanation')}")
        print(f"Code: {doc.get('code')}")
        print(f"Link: {doc.get('link')}")

if __name__ == "__main__":
    main()
