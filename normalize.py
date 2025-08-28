import uuid
import hashlib
import json
import os

 # Định nghĩa cấu trúc chung cho dữ liệu merge
COMMON_FIELDS = ["type", "explanation", "code", "tags", "link", "body"]

def detect_type(item):
     if not isinstance(item, dict):
         return None
     if "explanation" in item and ("code" in item or len(item.keys()) == 1):
         return "react_example"
     if "question_id" in item and "title" in item:
         return "stackoverflow"
     return None

def normalize_item(item):

    def make_unique_crawl_id(item):
        base = (str(item.get("code", "")) + str(item.get("explanation", "")) + str(item.get("link", ""))).encode("utf-8")
        if base.strip():
            return hashlib.md5(base).hexdigest()
        return str(uuid.uuid4())

    t = detect_type(item)
    if t == "react_example":
        crawl_id = make_unique_crawl_id(item)
        return {
            "crawl_id": crawl_id,
            "type": "react_example",
            "explanation": item.get("explanation", None),
            "code": item.get("code", None),
            "tags": None,
            "link": None,
            "body": None,
        }
    if t == "stackoverflow":
        # Lấy code đầu tiên trong code_blocks nếu có
        code = None
        if isinstance(item.get("code_blocks"), list) and len(item["code_blocks"]) > 0:
            code = item["code_blocks"][0].get("code", None)
        crawl_id = make_unique_crawl_id({
            "code": code,
            "explanation": item.get("title", ""),
            "link": item.get("link", "")
        })
        return {
            "crawl_id": crawl_id,
            "type": "stackoverflow",
            "explanation": item.get("title", None),
            "code": code,
            "tags": item.get("tags", None),
            "link": item.get("link", None),
            "body": item.get("body_markdown", None),
        }
    return None

def normalize_files(input_files, output_file):
    all_items = []
    for path in input_files:
        if not os.path.exists(path):
            print(f"File không tồn tại: {path}")
            continue
        with open(path, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except Exception as e:
                print(f"Lỗi đọc file {path}: {e}")
                continue
        # Nếu là list thì duyệt từng item, nếu là dict thì bọc vào list, nếu rỗng thì bỏ qua
        if isinstance(data, dict):
            data = [data]
        elif not isinstance(data, list):
            continue
        for item in data:
            norm = normalize_item(item)
            if norm:
                all_items.append(norm)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(all_items, f, ensure_ascii=False, indent=2)
    print(f"Đã chuẩn hóa và gộp dữ liệu vào {output_file}")

if __name__ == "__main__":
    # Ví dụ: nhập tên file nguồn ở đây
    input_files = [
        "react_code_examples.json",
        "reactjs_stackoverflow_questions.json"
    ]
    output_file = "normalized.json"
    normalize_files(input_files, output_file)
