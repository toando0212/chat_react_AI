import json
import os

# Hàm đếm số bản ghi trong normalized.json
def count_records_in_normalized():
    try:
        file_path = "normalized.json"
        if not os.path.exists(file_path):
            print(f"❌ File {file_path} không tồn tại.")
            return

        with open(file_path, "r", encoding="utf-8") as file:
            data = json.load(file)
            if isinstance(data, list):
                print(f"✅ File {file_path} có {len(data)} bản ghi.")
            else:
                print(f"⚠️ Dữ liệu trong file {file_path} không phải là danh sách.")
    except Exception as e:
        print(f"❌ Lỗi khi đọc file {file_path}: {str(e)}")

# Gọi hàm để đếm số bản ghi
count_records_in_normalized()