import argparse
import json
from pathlib import Path

QUIZ_ROOT = Path(__file__).parent / "quiz"
CATEGORY_DIR_MAP = {
    "漢字": "Kanji",
    "地理": "Geo",
}
DIFFICULTY_FOLDERS = {
    "easy": "Easy",
    "normal": "Normal",
    "hard": "Hard",
}


def normalize_answer(answer, choices):
    if isinstance(answer, int):
        return answer - 1
    if isinstance(answer, str):
        answer = answer.strip()
        if answer.isdigit():
            return int(answer) - 1
        letters = {"A": 0, "B": 1, "C": 2, "D": 3}
        if answer.upper() in letters:
            return letters[answer.upper()]
        if answer in choices:
            return choices.index(answer)
    return None


def validate_quiz_file(path: Path):
    if not path.exists():
        return False, "File does not exist"

    raw_text = path.read_text(encoding="utf-8", errors="ignore")
    if not raw_text.strip():
        return False, "Empty file"

    try:
        raw = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        return False, f"JSON decode error: {exc}"

    if not isinstance(raw, dict):
        return False, "Top-level JSON is not an object"

    question = raw.get("Question") or raw.get("question")
    choices = raw.get("Options") or raw.get("choices") or []
    answer = raw.get("Answer") if "Answer" in raw else raw.get("answer")

    if not question or not isinstance(question, str) or not question.strip():
        return False, "Missing or empty question"

    if not isinstance(choices, list) or len(choices) < 2:
        return False, "Choices must be a list with at least 2 items"

    normalized_choices = [str(item) for item in choices if item is not None]
    answer_index = normalize_answer(answer, normalized_choices)
    if answer_index is None or answer_index < 0 or answer_index >= len(normalized_choices):
        return False, "Invalid answer index"

    return True, None


def scan_quiz_files():
    invalid_files = []
    all_files = []

    for category_dir in CATEGORY_DIR_MAP.values():
        for difficulty_dir in DIFFICULTY_FOLDERS.values():
            folder = QUIZ_ROOT / category_dir / difficulty_dir
            if not folder.is_dir():
                continue
            for file_path in sorted(folder.glob("*.json")):
                all_files.append(file_path)
                valid, reason = validate_quiz_file(file_path)
                if not valid:
                    invalid_files.append((file_path, reason))
    return all_files, invalid_files


def repair_empty_file(path: Path, dry_run: bool):
    if dry_run:
        print(f"Would create placeholder for empty file: {path}")
        return
    placeholder = {
        "Question": "REPAIR: ここに問題文を入力してください。",
        "Options": ["選択肢A", "選択肢B", "選択肢C", "選択肢D"],
        "Answer": 1,
    }
    path.write_text(json.dumps(placeholder, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Created placeholder file: {path}")


def move_invalid_file(path: Path, dry_run: bool):
    invalid_dir = path.parent / "invalid"
    target = invalid_dir / path.name
    if dry_run:
        print(f"Would move invalid file {path} to {target}")
        return
    invalid_dir.mkdir(exist_ok=True)
    path.replace(target)
    print(f"Moved invalid file to {target}")


def rename_invalid_file(path: Path, dry_run: bool):
    target = path.with_suffix(path.suffix + ".invalid")
    if dry_run:
        print(f"Would rename invalid file {path} to {target}")
        return
    path.replace(target)
    print(f"Renamed invalid file to {target}")


def main():
    parser = argparse.ArgumentParser(description="Scan and repair quiz JSON files.")
    parser.add_argument("--dry-run", action="store_true", help="Show actions without modifying files")
    parser.add_argument("--repair-empty", action="store_true", help="Create placeholder JSON for empty quiz files")
    parser.add_argument("--move-invalid", action="store_true", help="Move invalid quiz files into an invalid/ subfolder")
    parser.add_argument("--rename-invalid", action="store_true", help="Rename invalid quiz files with .invalid suffix")
    args = parser.parse_args()

    all_files, invalid_files = scan_quiz_files()
    print(f"Scanned {len(all_files)} quiz files.")

    if not invalid_files:
        print("No invalid quiz files detected.")
        return

    print(f"Found {len(invalid_files)} invalid quiz files:")
    for path, reason in invalid_files:
        print(f"- {path}: {reason}")

    if args.repair_empty or args.move_invalid or args.rename_invalid:
        for path, reason in invalid_files:
            if reason == "Empty file" and args.repair_empty:
                repair_empty_file(path, args.dry_run)
            elif args.move_invalid:
                move_invalid_file(path, args.dry_run)
            elif args.rename_invalid:
                rename_invalid_file(path, args.dry_run)

    if args.dry_run:
        print("Dry run complete. No files modified.")


if __name__ == "__main__":
    main()
