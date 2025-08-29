
import re
import requests
import time
import json
from datetime import datetime
from tqdm import tqdm
from bs4 import BeautifulSoup

def read_api_key():
	with open("key.env", "r", encoding="utf-8") as f:
		for line in f:
			if line.startswith("STACK_EXCHANGE="):
				return line.strip().split("=", 1)[1]
	return None


# Trích xuất các đoạn code từ markdown (```...``` hoặc <code>...</code>)
def extract_code_blocks(body_markdown, body_html=None):
	code_blocks = []
	# Trích xuất code trong ``` ... ```
	if body_markdown:
		code_blocks += re.findall(r'```[a-zA-Z0-9]*\n([\s\S]*?)```', body_markdown, re.MULTILINE)
		code_blocks += re.findall(r'<code>([\s\S]*?)</code>', body_markdown, re.MULTILINE)
	# Nếu không có code trong markdown, thử lấy từ body_html
	if not code_blocks and body_html:
		soup = BeautifulSoup(body_html, "html.parser")
		# Lấy code trong <pre><code>...</code></pre>
		for pre in soup.find_all("pre"):
			code = pre.get_text("\n", strip=True)
			if code.strip():
				code_blocks.append(code.strip())
		# Lấy code trong <code>...</code> (không nằm trong <pre>)
		for code_tag in soup.find_all("code"):
			if code_tag.find_parent("pre") is None:
				code = code_tag.get_text("\n", strip=True)
				if code.strip():
					code_blocks.append(code.strip())
	return [c.strip() for c in code_blocks if c.strip()]

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
	return f"Đoạn code này liên quan đến: {title}"


def crawl_stackoverflow_reactjs(max_pages=150, page_size=50):
	api_key = read_api_key()
	crawl_id = datetime.now().strftime('%Y%m%d%H%M%S')
	# Đọc dữ liệu cũ nếu có
	existing_questions = []
	existing_ids = set()
	try:
		with open("reactjs_stackoverflow_questions.json", "r", encoding="utf-8") as f:
			existing_questions = json.load(f)
			existing_ids = set(q["question_id"] for q in existing_questions)
	except (FileNotFoundError, json.JSONDecodeError):
		existing_questions = []
		existing_ids = set()

	new_questions = []
	for page in tqdm(range(1, max_pages + 1), desc="Crawling pages"):
		url = (
			f"https://api.stackexchange.com/2.3/questions"
			f"?order=desc&sort=creation&tagged=reactjs&site=stackoverflow"
			f"&pagesize={page_size}&page={page}&filter=withbody"
			f"&key={api_key}"
		)
		resp = requests.get(url)
		if resp.status_code != 200:
			print(f"Error: {resp.status_code}")
			break
		data = resp.json()
		for item in data.get("items", []):
			qid = item["question_id"]
			if qid in existing_ids:
				continue  # Bỏ qua nếu đã có
			body_markdown = item.get("body_markdown", "")
			body_html = item.get("body", "")
			code_blocks = extract_code_blocks(body_markdown, body_html)
			code_blocks_meta = []
			for code in code_blocks:
				code_language = get_code_language(code)
				code_type = get_code_type(code)
				tags = extract_tags(item["title"], code)
				code_length = len(code.splitlines())
				code_meta = {
					"code": code,
					"code_language": code_language,
					"code_type": code_type,
					"tags": tags,
					"code_length": code_length,
					"explanation": explain_code(item["title"], code)
				}
				code_blocks_meta.append(code_meta)
			question = {
				"timestamp": datetime.now().isoformat(),
				"crawl_id": crawl_id,
				"question_id": qid,
				"title": item["title"],
				"link": item["link"],
				"tags": item["tags"],
				"creation_date": datetime.utcfromtimestamp(item["creation_date"]).isoformat(),
				"score": item["score"],
				"owner": item["owner"].get("display_name", "") if "owner" in item else "",
				"is_answered": item["is_answered"],
				"view_count": item["view_count"],
				"answer_count": item["answer_count"],
				"body_markdown": body_markdown,
				"body_html": body_html,
				"code_blocks": code_blocks_meta,
			}
			new_questions.append(question)
		time.sleep(1)  # Tránh bị giới hạn API

	all_questions = existing_questions + new_questions
	with open("reactjs_stackoverflow_questions.json", "w", encoding="utf-8") as f:
		json.dump(all_questions, f, ensure_ascii=False, indent=2)
	print(f"Đã lưu {len(new_questions)} câu hỏi mới, tổng cộng {len(all_questions)} câu hỏi vào reactjs_stackoverflow_questions.json")

if __name__ == "__main__":
	crawl_stackoverflow_reactjs(max_pages=150, page_size=50)  
