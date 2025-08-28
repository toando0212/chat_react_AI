# --- Chuẩn hóa dữ liệu và upsert cho cả react_code_examples và stackoverflow ---
import json
import google.generativeai as genai
import os
from pymongo import MongoClient
from pymongo import UpdateOne, InsertOne

from tqdm import tqdm

def read_env_key(key_name, env_file="key.env"):
	with open(env_file, "r", encoding="utf-8") as f:
		for line in f:
			if line.startswith(f"{key_name}="):
				return line.strip().split("=", 1)[1]
	return None

# INDEX_NAME = "chatcodeai"

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
	# Accept embeddings of various dimensions
	
	return flat


def resize_embedding(embedding, target_dim=1024):
	"""
	Điều chỉnh kích thước embedding về đúng kích thước đích.
	Nếu embedding nhỏ hơn, padding với 0.
	Nếu embedding lớn hơn, cắt bớt.
	"""
	current_dim = len(embedding)
	
	if current_dim == target_dim:
		return embedding
	
	if current_dim < target_dim:
		# Padding with zeros
		return embedding + [0.0] * (target_dim - current_dim)
	else:
		# Truncate
		return embedding[:target_dim]


def normalize_records(raw_records, source="react_code_example"):
	"""
	Chuẩn hóa dữ liệu về format:
	{
		"type": ...,
		"explanation": ...,
		"code": ...,
		"tags": [...],
		"link": ...,
		"body": ...
	}
	"""
	normalized = []
	for rec in raw_records:
		code_blocks = rec.get("code_blocks", None)
		crawl_id = rec.get("crawl_id", None)
		if code_blocks:
			for idx, block in enumerate(code_blocks):
				item = {
					"crawl_id": crawl_id,
					"type": source if source else rec.get("source", "stackoverflow"),
					"explanation": block.get("explanation", rec.get("explanation", "")),
					"code": block.get("code", ""),
					"tags": rec.get("tags", []),
					"link": rec.get("url", rec.get("link", "")),
					"body": rec.get("body_markdown", rec.get("body_html", "")) or ""
				}
				normalized.append(item)
		else:
			item = {
				"crawl_id": crawl_id,
				"type": source,
				"explanation": rec.get("explanation", ""),
				"code": rec.get("code", ""),
				"tags": rec.get("tags", []),
				"link": rec.get("url", rec.get("link", "")),
				"body": rec.get("body_markdown", rec.get("body_html", "")) or ""
			}
			normalized.append(item)
	return normalized


# --- Define the missing upsert_file function ---
def upsert_file(json_path, source="react_code_example"):
	import time
	
	with open(json_path, "r", encoding="utf-8") as f:
		data = json.load(f)
	records = normalize_records(data, source=source)

	# Kết nối MongoDB Atlas
	MONGODB_URI = read_env_key("MONGODB_URI")
	client = MongoClient(MONGODB_URI)
	db = client.get_default_database()
	collection = db[source]

	for item in tqdm(records, desc="Upserting to MongoDB", unit="item"):
		# Gộp metadata và embedding vào document
		doc = dict(item)
		explanation = item.get("explanation", "")
		code = item.get("code", "")

		# Đảm bảo code không phải None và chuyển thành chuỗi nếu cần
		if code is None:
			code = ""
		else:
			code = str(code)

		embed_text = code
		if explanation:
			if embed_text:
				embed_text += "\n" + explanation
			else:
				embed_text = explanation

		try:
			if not embed_text:
				print(f"Warning: Empty embed_text for item with crawl_id {item.get('crawl_id')}")
				embedding = [0.0] * 1024
			else:
				raw_embedding = get_embedding(embed_text)
				embedding = resize_embedding(raw_embedding, target_dim=1024)
		except Exception as e:
			print(f"Error generating embedding for item: {item.get('crawl_id')}. Error: {e}")
			embedding = [0.0] * 1024  # Default embedding in case of error

		doc["embedding"] = embedding
		crawl_id = doc.get("crawl_id", None)

		if crawl_id:
			collection.update_one({"crawl_id": crawl_id}, {"$set": doc}, upsert=True)
		else:
			collection.insert_one(doc)

	client.close()


def main():
	# Cấu hình Gemini (embedding ngoài, không phát sinh phí Pinecone embedding)
	GEMINI_API_KEY = read_env_key("GEMINI_API_KEY")
	genai.configure(api_key=GEMINI_API_KEY)

	# Upsert normalized.json nếu tồn tại
	
	upsert_file("normalized.json", source="normalized")
	

if __name__ == "__main__":
	main()
