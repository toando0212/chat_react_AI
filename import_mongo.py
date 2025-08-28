import json
from pymongo import MongoClient, UpdateOne
import os
from tqdm import tqdm

def read_env_key(key_name, env_file="key.env"):
    with open(env_file, "r", encoding="utf-8") as f:
        for line in f:
            if line.startswith(f"{key_name}="):
                return line.strip().split("=", 1)[1]
    return None

def import_to_mongodb(json_path="normalized.json", collection_name="normalized", batch_size=100):
    """
    Import dữ liệu từ file JSON vào MongoDB với bulk upsert
    sử dụng crawl_id làm trường để tìm kiếm document cần update
    """
    # Đọc dữ liệu từ file
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    if not data:
        print(f"Không có dữ liệu trong file {json_path}")
        return
    
    # Kết nối MongoDB
    MONGODB_URI = read_env_key("MONGODB_URI")
    client = MongoClient(MONGODB_URI)
    db = client.get_default_database()
    collection = db[collection_name]
    
    # Tạo chỉ mục cho crawl_id nếu chưa có
    collection.create_index("crawl_id", unique=True)
    
    # Chia thành các batch để upsert
    operations = []
    for item in data:
        crawl_id = item.get("crawl_id")
        if not crawl_id:
            print(f"Bỏ qua item không có crawl_id: {item}")
            continue
        
        # UpdateOne với upsert=True: nếu tìm thấy thì cập nhật, không thì tạo mới
        operations.append(
            UpdateOne(
                {"crawl_id": crawl_id},
                {"$set": item},
                upsert=True
            )
        )
    
    # Upsert theo batch
    total_batches = (len(operations) + batch_size - 1) // batch_size
    total_success = 0
    
    print(f"Đang upsert {len(operations)} document vào collection {collection_name}...")
    for i in tqdm(range(0, len(operations), batch_size), total=total_batches):
        batch = operations[i:i + batch_size]
        result = collection.bulk_write(batch)
        total_success += result.upserted_count + result.modified_count
    
    print(f"Hoàn thành: Đã upsert {total_success}/{len(operations)} document")
    client.close()

if __name__ == "__main__":
    # Đảm bảo file normalized.json đã được tạo trước
    if not os.path.exists("normalized.json"):
        print("File normalized.json không tồn tại. Hãy chạy normalize.py trước.")
        exit(1)
    
    import_to_mongodb()
