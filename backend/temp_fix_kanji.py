import json
from pathlib import Path

root = Path('backend/quiz/Kanji')
if not root.exists():
    raise SystemExit(f'Path not found: {root}')

fixed = []


def fix_value(value):
    if isinstance(value, str):
        if value.startswith('～～') and value.endswith('～～') and len(value) >= 4:
            return value[2:-2]
        return value
    if isinstance(value, list):
        return [fix_value(v) for v in value]
    if isinstance(value, dict):
        return {k: fix_value(v) for k, v in value.items()}
    return value

for path in sorted(root.rglob('*.json')):
    text = path.read_text(encoding='utf-8')
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        print(f'INVALID JSON: {path} -> {e}')
        continue
    new_data = fix_value(data)
    new_text = json.dumps(new_data, ensure_ascii=False, indent=4)
    if new_text != text.replace('\r\n', '\n'):
        path.write_text(new_text + '\n', encoding='utf-8')
        fixed.append(str(path))

print(f'Updated {len(fixed)} files')
for p in fixed:
    print(p)
