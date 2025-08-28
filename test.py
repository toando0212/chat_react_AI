
import json
from collections import Counter
import os
import hashlib
import uuid

def count_duplicate_crawl_id(json_path="react_code_examples.json"):
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        crawl_ids = [item.get("crawl_id") for item in data if item.get("crawl_id")]
        counter = Counter(crawl_ids)
        duplicates = {k: v for k, v in counter.items() if v > 1}
        print(f"File: {json_path}")
        print(f"Tổng số item: {len(data)}")
        print(f"Số lượng crawl_id bị trùng lặp: {len(duplicates)}")
        if duplicates:
            print("crawl_id trùng lặp và số lần xuất hiện:")
            for k, v in sorted(duplicates.items(), key=lambda x: x[1], reverse=True)[:5]:
                print(f"{k}: {v}")
        return duplicates
    except FileNotFoundError:
        print(f"File {json_path} không tồn tại")
        return {}

# def count_duplicate_crawl_id2(json_path="reactjs_stackoverflow_questions.json"):
#     try:
#         with open(json_path, "r", encoding="utf-8") as f:
#             data = json.load(f)
#         crawl_ids = [item.get("crawl_id") for item in data if item.get("crawl_id")]
#         counter = Counter(crawl_ids)
#         duplicates = {k: v for k, v in counter.items() if v > 1}
#         print(f"File: {json_path}")
#         print(f"Tổng số item: {len(data)}")
#         print(f"Số lượng crawl_id bị trùng lặp: {len(duplicates)}")
#         if duplicates:
#             print("crawl_id trùng lặp và số lần xuất hiện:")
#             for k, v in sorted(duplicates.items(), key=lambda x: x[1], reverse=True)[:5]:
#                 print(f"{k}: {v}")
#         return duplicates
#     except FileNotFoundError:
#         print(f"File {json_path} không tồn tại")
#         return {}

def validate_normalized_json(input_path="normalized.json"):
    """Kiểm tra tính duy nhất của crawl_id trong file normalized.json"""
    try:
        with open(input_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        crawl_ids = [item.get("crawl_id") for item in data if item.get("crawl_id")]
        counter = Counter(crawl_ids)
        duplicates = {k: v for k, v in counter.items() if v > 1}
        
        print(f"\nKiểm tra file normalized: {input_path}")
        print(f"Tổng số item: {len(data)}")
        print(f"Số lượng crawl_id: {len(crawl_ids)}")
        print(f"Số lượng crawl_id duy nhất: {len(set(crawl_ids))}")
        
        if duplicates:
            print(f"CẢNH BÁO: Tìm thấy {len(duplicates)} crawl_id bị trùng lặp!")
            for k, v in sorted(duplicates.items(), key=lambda x: x[1], reverse=True)[:5]:
                print(f"{k}: {v}")
            return False
        else:
            print("Tất cả crawl_id đều duy nhất. ✓")
            return True
    except FileNotFoundError:
        print(f"File {input_path} không tồn tại")
        return False

def test_crawl_id_stability():
    """Kiểm tra tính ổn định của crawl_id qua các lần chạy normalize"""
    
    # Chạy normalize.py để tạo file normalized.json
    import subprocess
    print("\nĐang chạy normalize.py lần 1...")
    subprocess.run(["python", "normalize.py"])
    
    # Đọc file kết quả lần 1
    with open("normalized.json", "r", encoding="utf-8") as f:
        data1 = json.load(f)
    crawl_ids1 = {item.get("crawl_id") for item in data1 if item.get("crawl_id")}
    
    # Đổi tên file kết quả (xoá file cũ nếu tồn tại để tránh lỗi)
    tmp_file = "normalized_run1.json"
    if os.path.exists(tmp_file):
        os.remove(tmp_file)
    os.rename("normalized.json", tmp_file)
    
    # Chạy normalize.py lần 2
    print("\nĐang chạy normalize.py lần 2...")
    subprocess.run(["python", "normalize.py"])
    
    # Đọc file kết quả lần 2
    with open("normalized.json", "r", encoding="utf-8") as f:
        data2 = json.load(f)
    crawl_ids2 = {item.get("crawl_id") for item in data2 if item.get("crawl_id")}
    
    # So sánh kết quả
    matching_ids = crawl_ids1.intersection(crawl_ids2)
    
    print(f"\nKết quả kiểm tra tính ổn định:")
    print(f"Số lượng crawl_id lần 1: {len(crawl_ids1)}")
    print(f"Số lượng crawl_id lần 2: {len(crawl_ids2)}")
    print(f"Số lượng crawl_id giống nhau: {len(matching_ids)}")
    
    if len(matching_ids) == len(crawl_ids1) and len(matching_ids) == len(crawl_ids2):
        print("THÀNH CÔNG: Tất cả crawl_id đều ổn định qua các lần chạy. ✓")
        # Xóa file tạm
        os.remove("normalized_run1.json")
        return True
    else:
        print("LỖI: crawl_id không ổn định qua các lần chạy!")
        return False

if __name__ == "__main__":
    print("=== KIỂM TRA FILE GỐC ===")
    if os.path.exists("react_code_examples.json"):
        count_duplicate_crawl_id("react_code_examples.json")
    
    if os.path.exists("reactjs_stackoverflow_questions.json"):
        count_duplicate_crawl_id("reactjs_stackoverflow_questions.json")
    
    print("\n=== KIỂM TRA FILE NORMALIZED ===")
    if os.path.exists("normalized.json"):
        validate_normalized_json()
    
    choice = input("\nBạn có muốn kiểm tra tính ổn định của crawl_id qua các lần chạy không? (y/n): ")
    if choice.lower() == 'y':
        test_crawl_id_stability()
