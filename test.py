
import json


def count_duplicate_crawl_id(json_path="normalized.json"):
	with open(json_path, "r", encoding="utf-8") as f:
		data = json.load(f)
	crawl_ids = [item.get("crawl_id") for item in data if item.get("crawl_id")]
	from collections import Counter
	counter = Counter(crawl_ids)
	duplicates = {k: v for k, v in counter.items() if v > 1}
	print(f"Số lượng crawl_id bị trùng lặp: {len(duplicates)}")
	if duplicates:
		print("crawl_id trùng lặp và số lần xuất hiện:")
		for k, v in duplicates.items():
			print(f"{k}: {v}")
	return duplicates

if __name__ == "__main__":

	count_duplicate_crawl_id()
