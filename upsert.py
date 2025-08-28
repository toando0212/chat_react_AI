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


def normalize_records(raw_records, source="normalized"):
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
	# If records are already normalized by normalize.py, use them directly
	if source == "normalized":
		return raw_records
	# Otherwise, flatten code_blocks entries for react or stackoverflow crawls
	normalized = []
	for rec in raw_records:
		code_blocks = rec.get("code_blocks")
		crawl_id = rec.get("crawl_id")
		if isinstance(code_blocks, list) and code_blocks:
			for block in code_blocks:
				item = {
					"crawl_id": crawl_id,
					"type": source,
					"explanation": block.get("explanation", rec.get("explanation", "")),
					"code": block.get("code", ""),
					"tags": rec.get("tags", []),
					"link": rec.get("url", rec.get("link", "")),
					# preserve code_language if available
					"code_language": block.get("code_language", None),
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
				"code_language": rec.get("code_language", None),
			}
			normalized.append(item)
	return normalized


# --- Define the missing upsert_file function ---
def upsert_file(json_path, source="normalized", target_collection=None):
	import time
	
	with open(json_path, "r", encoding="utf-8") as f:
		data = json.load(f)
	records = normalize_records(data, source=source)

	# Kết nối MongoDB Atlas
	MONGODB_URI = read_env_key("MONGODB_URI")
	client = MongoClient(MONGODB_URI)
	db = client.get_default_database()
	# Sử dụng target_collection nếu được cung cấp, nếu không sử dụng source làm tên collection
	collection_name = target_collection if target_collection else source
	collection = db[collection_name]

	
	# Tạo unique index cho crawl_id
	collection.create_index("crawl_id", unique=True)
	
	# Xử lý tất cả records với bulk operations để tăng hiệu suất
	operations = []
	batch_size = 50  # Giảm batch size vì phải gọi embedding API
	
	for item in tqdm(records, desc="Generating embeddings and preparing upsert", unit="item"):
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

		doc = dict(item)
		doc["embedding"] = embedding
		crawl_id = doc.get("crawl_id")
		
		if crawl_id:
			# Sử dụng UpdateOne với upsert để tránh trùng lặp
			operations.append(
				UpdateOne(
					{"crawl_id": crawl_id},
					{"$set": doc},
					upsert=True
				)
			)
		
		# Thực hiện bulk write khi đạt batch_size
		if len(operations) >= batch_size:
			result = collection.bulk_write(operations)
			operations = []
			time.sleep(0.1)  # Tránh rate limit của Gemini API
	
	# Xử lý batch cuối cùng
	if operations:
		result = collection.bulk_write(operations)
		print(f"Final batch: {result.upserted_count} inserted, {result.modified_count} updated")
		
	client.close()


def main():
	# Cấu hình Gemini (embedding ngoài, không phát sinh phí Pinecone embedding)
	GEMINI_API_KEY = read_env_key("GEMINI_API_KEY")
	genai.configure(api_key=GEMINI_API_KEY)

	upsert_file("normalized.json", source="normalized", target_collection="normalized")


if __name__ == "__main__":
	main()
