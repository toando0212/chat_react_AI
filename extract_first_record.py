
import json
import re

def split_content(content):
    code_blocks = re.findall(r'```(?:\w*\n)?(.*?)```', content, flags=re.DOTALL)
    text = re.sub(r'```(?:\w*\n)?.*?```', '', content, flags=re.DOTALL).strip()
    return text, code_blocks

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
        # normalize assistant content if exists
        if "messages" in obj:
            for msg in obj["messages"]:
                if msg.get("role") == "assistant" and isinstance(msg.get("content"), str):
                    text, code_blocks = split_content(msg["content"])
                    msg["text"] = text
                    msg["code"] = code_blocks
        records.append(obj)
        if len(records) >= limit:
            break

if records:
    with open(output_path, "w", encoding="utf-8") as out:
        json.dump(records, out, ensure_ascii=False, indent=2)
    print(f"Đã trích xuất và chuẩn hóa {len(records)} bản ghi đầu tiên ra {output_path}")
else:
    print("Không tìm thấy bản ghi hợp lệ trong file.")