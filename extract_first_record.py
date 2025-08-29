import json

jsonl_path = "dataset_react.jsonl"
output_path = "first_record.json"
limit = 1000
records = []

with open(jsonl_path, "r", encoding="utf-8") as f:
    for line in f:
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        records.append(obj)
        if len(records) >= limit:
            break

if records:
    with open(output_path, "w", encoding="utf-8") as out:
        json.dump(records, out, ensure_ascii=False, indent=2)
    print(f"Đã trích xuất {len(records)} bản ghi đầu tiên ra {output_path}")
else:
    print("Không tìm thấy bản ghi hợp lệ trong file.")