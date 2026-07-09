import json
import logging
import os
import random

logger = logging.getLogger(__name__)
QUIZ_ROOT = os.path.join(os.path.dirname(__file__), "quiz")
CATEGORY_DIR_MAP = {
    "漢字": "Kanji",
    "地理": "Geo",
}
DIFFICULTY_FOLDERS = {
    "easy": "Easy",
    "normal": "Normal",
    "hard": "Hard",
}


def _normalize_answer(answer, choices):
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


def _load_questions_from_file(file_path):
    try:
        with open(file_path, encoding="utf-8") as f:
            raw = json.load(f)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        logger.warning("Skipping invalid quiz file %s: %s", file_path, exc)
        return None
    except OSError as exc:
        logger.warning("Unable to read quiz file %s: %s", file_path, exc)
        return None

    if not isinstance(raw, dict):
        logger.warning("Skipping quiz file %s because top-level JSON is not an object", file_path)
        return None

    question = raw.get("Question") or raw.get("question")
    choices = raw.get("Options") or raw.get("choices") or []
    answer = raw.get("Answer") if "Answer" in raw else raw.get("answer")

    if not isinstance(choices, list):
        choices = []
    choices = [str(item) for item in choices if item is not None]

    answer_index = _normalize_answer(answer, choices)
    if answer_index is None or answer_index < 0 or answer_index >= len(choices):
        logger.warning("Skipping quiz file %s because answer is invalid", file_path)
        return None

    if not question or not isinstance(question, str):
        logger.warning("Skipping quiz file %s because question text is missing", file_path)
        return None

    question_text = question.strip()
    if not question_text:
        logger.warning("Skipping quiz file %s because question text is empty", file_path)
        return None

    if len(choices) < 2:
        logger.warning("Skipping quiz file %s because it has fewer than 2 choices", file_path)
        return None

    return {
        "id": os.path.relpath(file_path, QUIZ_ROOT).replace("\\", "/"),
        "question": question_text,
        "choices": choices,
        "answer": answer_index,
    }


def load_quiz_bank():
    bank = {}
    for category_name, folder_name in CATEGORY_DIR_MAP.items():
        category_path = os.path.join(QUIZ_ROOT, folder_name)
        if not os.path.isdir(category_path):
            continue

        bank[category_name] = {}
        for diff_key, diff_dir in DIFFICULTY_FOLDERS.items():
            diff_path = os.path.join(category_path, diff_dir)
            questions = []
            if os.path.isdir(diff_path):
                for file_name in sorted(os.listdir(diff_path)):
                    if not file_name.lower().endswith(".json"):
                        continue
                    file_path = os.path.join(diff_path, file_name)
                    loaded = _load_questions_from_file(file_path)
                    if loaded is not None:
                        questions.append(loaded)
            bank[category_name][diff_key] = questions
    return bank


QUIZ_BANK = load_quiz_bank()
DEFAULT_CATEGORY = next(iter(QUIZ_BANK), None)
DIFFICULTIES = ["easy", "normal", "hard"]


def difficulty_for_cell(x, y):
    """6x6盤面の外側に向かって難易度を上げる"""
    
    if (x == 0 or x == 5) and (y == 0 or y == 5):
        return "hard"
    if (x,y) in [(1,2),(1,3),(2,1),(2,4),(3,1),(3,4),(4,2),(4,3)]:
        return "easy"
    if (2 <= x <= 3) and (2 <= y <= 3):
        return "none"
    return "normal"

def create_quiz_board(category):
    """6x6のクイズボードを生成する"""
    easy_questions = QUIZ_BANK.get(category, {}).get("easy", [])
    normal_questions = QUIZ_BANK.get(category, {}).get("normal", [])
    hard_questions = QUIZ_BANK.get(category, {}).get("hard", [])

    random.shuffle(easy_questions)
    random.shuffle(normal_questions)
    random.shuffle(hard_questions)
    print(normal_questions,len(normal_questions))
    easy_iter = iter(easy_questions)
    normal_iter = iter(normal_questions)
    hard_iter = iter(hard_questions)
    board = []
    used_question_ids = set()
    for y in range(6):
        row = []
        for x in range(6):
            difficulty = difficulty_for_cell(x, y)
            if difficulty == "easy":
                question = next(easy_iter, None)
            elif difficulty == "normal":
                question = next(normal_iter, None)  
            elif difficulty == "hard":
                question = next(hard_iter, None)
            else:
                continue  # 難易度が "none" の場合はスキップ
            print(x,y,question)
            if question is None:
                raise RuntimeError(f"不足しています: {category} の {difficulty} で一意なクイズが足りません。")
            used_question_ids.add(question.get("id"))
            row.append({
                "question": question["question"],
                "choices": question["choices"],
                "correct": question["answer"],
                "difficulty": difficulty,
                "removedChoices": [],
            })
        board.append(row)
    return board
