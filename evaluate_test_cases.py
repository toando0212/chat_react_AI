import os
import subprocess
import json
import sys
import platform
from tqdm import tqdm

# Thư mục chứa các file TSX component
directory = 'test_cases'

results = []

# Hàm trợ giúp để tìm npx command phù hợp
def find_working_npx_command():
    if platform.system() == 'Windows':
        # Trên Windows, thử lần lượt các biến thể của npx
        commands = ['npx.cmd', 'npx', 'npx.exe']
    else:
        # Trên Linux/Mac
        commands = ['npx']
        
    for cmd in commands:
        try:
            # Thử chạy thử command với lệnh --version
            result = subprocess.run([cmd, '--version'], 
                                   capture_output=True, text=True)
            if result.returncode == 0:
                print(f"Đã tìm thấy lệnh npx hoạt động: {cmd}")
                return cmd
        except FileNotFoundError:
            continue
    
    # Nếu không tìm thấy command nào hoạt động
    print("KHÔNG TÌM THẤY LỆNH NPX HOẠT ĐỘNG!")
    print("Hãy đảm bảo Node.js được cài đặt đúng cách.")
    sys.exit(1)

# Tìm npx command phù hợp
npx_command = find_working_npx_command()

# Duyệt qua các file .tsx với tqdm
tsx_files = [f for f in os.listdir(directory) if f.endswith('.tsx')]

# Kiểm tra trước xem có tsconfig.json không
tsconfig_path = os.path.join(directory, 'tsconfig.json')
use_tsconfig = os.path.exists(tsconfig_path)

for filename in tqdm(tsx_files, desc="Đang kiểm tra TSX", unit="file"):
    filepath = os.path.join(directory, filename)
    # Chạy TypeScript compiler với tsconfig nếu có, hoặc thêm các cờ cần thiết
    try:
        if use_tsconfig:
            cmd = [npx_command, 'tsc', '--noEmit', '--project', tsconfig_path]
            # Chỉ kiểm tra một file cụ thể, không phải toàn bộ project
            # Dòng này sẽ tạm bỏ vì TypeScript ưu tiên chạy toàn bộ dự án khi có --project
        else:
            cmd = [
                npx_command, 'tsc', 
                '--noEmit', 
                '--jsx', 'react-jsx',
                '--esModuleInterop',
                '--allowSyntheticDefaultImports',
                '--skipLibCheck',
                '--lib', 'es2020,dom',
                filepath
            ]
        
        # Chạy lệnh
        proc = subprocess.run(cmd, capture_output=True, text=True)
        passed = proc.returncode == 0
        
        # Combine stderr and stdout to capture all error messages
        error_output = (proc.stderr or '') + (proc.stdout or '')
        
        # Nếu dùng tsconfig và có lỗi, thử log lỗi cụ thể cho file này
        if use_tsconfig and not passed:
            # Thử tìm lỗi cụ thể cho file này trong output
            errors_for_file = []
            for line in error_output.splitlines():
                if filename in line:
                    errors_for_file.append(line)
            
            # Nếu tìm thấy lỗi cụ thể, chỉ hiển thị những lỗi đó
            if errors_for_file:
                error_output = '\n'.join(errors_for_file)
        
        results.append({
            'file': filename,
            'passed': passed,
            'errors': error_output.strip() if not passed else ''
        })
    except Exception as e:
        # Xử lý nếu có lỗi khi chạy command
        print(f"Lỗi khi kiểm tra file {filename}: {str(e)}")
        results.append({
            'file': filename, 
            'passed': False,
            'errors': f"Lỗi hệ thống: {str(e)}"
        })

# Tính tổng và pass rate
total = len(results)
passed_count = sum(1 for r in results if r['passed'])
pass_rate = passed_count / total * 100 if total > 0 else 0

# Ghi kết quả ra file JSON
output_file = 'syntax_check_results.json'
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump({
        'total': total,
        'passed': passed_count,
        'pass_rate_percent': pass_rate,
        'details': results
    }, f, ensure_ascii=False, indent=2)

# In tóm tắt lên console
print(f"Đã kiểm tra {total} file.\nPass: {passed_count}/{total} ({pass_rate:.2f}%).")
print(f"Chi tiết kết quả được lưu ở {output_file}.")
