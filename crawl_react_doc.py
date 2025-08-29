from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

import time
import tqdm
import json
import hashlib
from datetime import datetime


def get_code_language(code_text):
	if code_text.strip().startswith('import') or 'function' in code_text or 'export default' in code_text:
		return 'javascript/jsx'
	if code_text.strip().startswith('<') and code_text.strip().endswith('>'):
		return 'html/jsx'
	if code_text.strip().startswith('npm') or code_text.strip().startswith('yarn'):
		return 'shell'
	return 'unknown'

def get_code_type(code_text):
	if 'function' in code_text:
		return 'function'
	if 'class' in code_text:
		return 'class'
	if 'export default' in code_text:
		return 'component'
	if code_text.strip().startswith('import'):
		return 'import'
	if code_text.strip().startswith('npm') or code_text.strip().startswith('yarn'):
		return 'command'
	return 'snippet'

def extract_tags(title, code_text):
	tags = set()
	for word in title.lower().replace('–', '').replace('-', '').split():
		if word not in ['react', 'a', 'the', 'to', 'of', 'in', 'and', 'for', 'on', 'with', 'is', 'by', 'as', 'an', 'at', 'from']:
			tags.add(word)
	if 'useState' in code_text:
		tags.add('state')
	if 'useEffect' in code_text:
		tags.add('effect')
	if 'useReducer' in code_text:
		tags.add('reducer')
	if 'props' in code_text:
		tags.add('props')
	if 'export default' in code_text:
		tags.add('component')
	return list(tags)

def explain_code(title, code_text):
	# Simple explanation using title, can be improved with AI
	return f"{title}"

def crawl_react_dev_code_examples():
	driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
	driver.get("https://react.dev/learn")

	# Lấy tất cả link bài học trong mục Learn
	links = driver.find_elements(By.CSS_SELECTOR, "a[href^='/learn/']")
	lesson_urls = set([l.get_attribute("href") for l in links if l.get_attribute("href")])

	all_code_blocks = []
	seen_hashes = set()
	crawl_id = hashlib.md5(str(datetime.now()).encode()).hexdigest()
	timestamp = datetime.now().isoformat()

	for url in tqdm.tqdm(lesson_urls, desc="Crawling lessons"):
		driver.get(url)
		time.sleep(1)  # Chờ trang load
		title = driver.title
		# Lấy section/chapter từ title nếu có
		section = title.split('–')[0].strip() if '–' in title else title
		code_blocks = driver.find_elements(By.TAG_NAME, "pre")
		for block in code_blocks:
			code_text = block.text.strip()
			if code_text:
				code_hash = hashlib.md5(code_text.encode()).hexdigest()
				is_duplicate = code_hash in seen_hashes
				seen_hashes.add(code_hash)
				code_language = get_code_language(code_text)
				code_type = get_code_type(code_text)
				tags = extract_tags(title, code_text)
				code_length = len(code_text.splitlines())
				item = {
					"timestamp": timestamp,
					"crawl_id": crawl_id,
					"url": url,
					"source_title": title,
					"section": section,
					"code": code_text,
					"code_language": code_language,
					"code_type": code_type,
					"tags": tags,
					"code_length": code_length,
					"is_duplicate": is_duplicate,
					"topic": section,
					"purpose": section,
					"explanation": explain_code(title, code_text)
				}
				all_code_blocks.append(item)

	driver.quit()

	# Lưu các đoạn code vào file JSON
	with open("react_code_examples.json", "w", encoding="utf-8") as f:
		json.dump(all_code_blocks, f, ensure_ascii=False, indent=2)
	print(f"Đã lưu {len(all_code_blocks)} đoạn code vào react_code_examples.json")

if __name__ == "__main__":
	crawl_react_dev_code_examples()

