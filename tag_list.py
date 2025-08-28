
import json
from collections import Counter

def main():
	tag_counter = Counter()
	with open("reactjs_stackoverflow_questions.json", "r", encoding="utf-8") as f:
		# Đọc từng dòng để tránh load toàn bộ file lớn vào RAM nếu file quá lớn
		data = json.load(f)
		for q in data:
			tags = q.get("tags", [])
			tag_counter.update(tags)


	print("Các tag xuất hiện và số lần xuất hiện:")
	for tag, count in tag_counter.most_common():
		print(f"{tag}: {count}")
	print("\nTổng số tag khác nhau:", len(tag_counter))
	

if __name__ == "__main__":
	main()
