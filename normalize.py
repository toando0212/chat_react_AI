import uuid
import hashlib
import json
import os
import argparse
import glob

# Định nghĩa cấu trúc chung cho dữ liệu merge
COMMON_FIELDS = ["type", "explanation", "code", "tags", "link", "body"]

def detect_type(item):
    if not isinstance(item, dict):
        return None
    # React examples have code and explanation fields
    if "explanation" in item and "code" in item:
        return "react_example"
    if "question_id" in item and "title" in item:
        return "stackoverflow"
    return None

def normalize_item(item):

    def make_unique_crawl_id(item):
        # Ưu tiên sử dụng crawl_id gốc nếu có và là dạng UUID hoặc MD5 (32 ký tự hex)
        original_id = item.get("crawl_id")
        if original_id and (len(original_id) == 32 or len(original_id) == 36):
            return original_id
            
        # Nếu là question_id của StackOverflow, tạo ID ổn định từ đó
        if item.get("question_id"):
            return f"so_{item.get('question_id')}"
            
        # Trường hợp khác, tạo ID từ nội dung
        unique_parts = []
        # Lấy đường dẫn làm phần chính của ID
        if item.get("url"):
            unique_parts.append(str(item.get("url", "")))
        elif item.get("link"):
            unique_parts.append(str(item.get("link", "")))
            
        # Thêm một phần code để phân biệt các đoạn code khác nhau cùng URL
        if item.get("code"):
            # Chỉ dùng 20 ký tự đầu của code để tránh ID quá dài
            unique_parts.append(str(item.get("code", ""))[:20])
        
        base = "|".join(unique_parts).encode("utf-8")
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
            "tags": item.get("tags", None),
            "link": item.get("url", item.get("link", None)),
            "code_language": item.get("code_language", None),
        }
    if t == "stackoverflow":
        # Lấy code đầu tiên trong code_blocks nếu có
        code = None
        code_language = None
        if isinstance(item.get("code_blocks"), list) and len(item["code_blocks"]) > 0:
            first = item["code_blocks"][0]
            code = first.get("code", None)
            code_language = first.get("code_language", None)
            
        # Tạo crawl_id ổn định bằng cách giữ crawl_id gốc hoặc tạo từ question_id
        so_item = {
            "crawl_id": item.get("crawl_id"),
            "question_id": item.get("question_id"),
            "code": code,
            "explanation": item.get("title", ""),
            "link": item.get("link", "") or item.get("url", "")
        }
        crawl_id = make_unique_crawl_id(so_item)
        
        return {
            "crawl_id": crawl_id,
            "type": "stackoverflow",
            "explanation": item.get("title", None),
            "code": code,
            "tags": item.get("tags", None),
            "link": item.get("url", item.get("link", None)),
            "code_language": code_language,
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
    # Parse command-line arguments for flexible input and output
    parser = argparse.ArgumentParser(description="Normalize and merge JSON crawl data.")
    parser.add_argument('-i', '--input', nargs='*', help='List of input JSON files to process. Defaults to all .json files in directory.')
    parser.add_argument('-o', '--output', default='normalized.json', help='Output JSON file name')
    args = parser.parse_args()
    # Discover input files dynamically if not provided
    if args.input:
        input_files = args.input
    else:
        # All JSON files except the output file and any normalized outputs
        input_files = [f for f in glob.glob('*.json')
                       if f != args.output and not f.startswith('normalized')]
    print(f"Found {len(input_files)} input files: {input_files}")
    normalize_files(input_files, args.output)
