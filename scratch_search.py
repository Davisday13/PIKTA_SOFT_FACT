import sys

def search_in_file(filepath, queries):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        for i, line in enumerate(lines):
            if any(q.lower() in line.lower() for q in queries):
                print(f"{filepath}:{i+1}: {line.strip()[:100]}")
    except Exception as e:
        print(f"Error reading {filepath}: {e}")

search_in_file(r"c:\Users\DAVIS\Desktop\PIK'TA_SOFT_FACT - copia\main_app.py", ["json.loads"])
