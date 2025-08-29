import os
import json

# Paths configuration
input_json = "first_record.json"  # normalized JSON with text/code fields
cases_dir = "test_cases"

# Load normalized records
with open(input_json, 'r', encoding='utf-8') as f:
    records = json.load(f)

# Create test_cases directory if not exist
os.makedirs(cases_dir, exist_ok=True)

# Generate individual code files and corresponding test cases
for idx, rec in enumerate(records, start=1):
    # Combine all assistant code blocks
    code_blocks = []
    for msg in rec.get('messages', []):
        if msg.get('role') == 'assistant' and isinstance(msg.get('code'), list):
            code_blocks.extend(msg['code'])
    if not code_blocks:
        continue  # skip if no code

    # Use the first code block as the component
    component_code = code_blocks[0]
    component_filename = os.path.join(cases_dir, f"AppCase{idx}.tsx")
    # Write the React component file
    with open(component_filename, 'w', encoding='utf-8') as cf:
        cf.write(component_code)


print(f"Generated {idx} code cases and tests in '{cases_dir}' directory.")
