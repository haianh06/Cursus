import os
import re

FORBIDDEN_PATTERNS = [
    r'indigo',
    r'purple',
    r'violet',
    r'#4F46E5',
    r'#1E1B4B',
    r'#312E81',
    r'#4338CA',
    r'#6366F1',
    r'#818CF8',
    r'#0F1420',
    r'#181F33',
    r'#111625',
    r'#2B3654'
]

SRC_DIR = r"d:\VINAI_Team_093\P-093\frontend\src"

def verify_tokens():
    violations = []
    for root, _, files in os.walk(SRC_DIR):
        for file in files:
            if file.endswith(('.jsx', '.js', '.css', '.html')):
                filepath = os.path.join(root, file)
                with open(filepath, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    for idx, line in enumerate(lines, 1):
                        for pattern in FORBIDDEN_PATTERNS:
                            if re.search(pattern, line, re.IGNORECASE):
                                violations.append(f"{file}:{idx} -> Pattern '{pattern}' found in line: {line.strip()}")
    
    if violations:
        print(f"[ERROR] FOUND {len(violations)} TOKEN VIOLATIONS:")
        for v in violations[:30]:
            print(f"  - {v}")
        return False
    else:
        print("[SUCCESS] VERIFICATION PASSED: 0 TOKEN VIOLATIONS FOUND! Ink & Citrine Design System is 100% compliant.")
        return True

if __name__ == "__main__":
    verify_tokens()
