import json
import os
import random

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


def _load_questions_from_file(file_path):
    with open(file_path, encoding="utf-8") as f:
        raw = json.load(f)

    question = raw.get("Question") or raw.get("question")
    choices = raw.get("Options") or raw.get("choices") or []
    answer = raw.get("Answer") if "Answer" in raw else raw.get("answer")

    if isinstance(answer, str) and answer.isdigit():
        answer = int(answer)
    if isinstance(answer, int):
        answer = answer - 1

    return {
        "question": question,
        "choices": choices,
        "answer": answer,
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
                    if loaded["question"] and loaded["choices"] and loaded["answer"] is not None:
                        questions.append(loaded)
            bank[category_name][diff_key] = questions
    return bank


QUIZ_BANK = load_quiz_bank()
DEFAULT_CATEGORY = next(iter(QUIZ_BANK), None)
DIFFICULTIES = ["easy", "normal", "hard"]


def difficulty_for_cell(x, y):
    """6x6盤面の外側に向かって難易度を上げる"""
    center = 2.5
    distance = abs(x - center) + abs(y - center)
    if distance <= 2:
        return "easy"
    if distance <= 4:
        return "normal"
    return "hard"


def pick_question(category, difficulty, excluded_indices=None):
    """問題プールからランダムに1問を選ぶ"""
    pool = QUIZ_BANK.get(category, {}).get(difficulty, [])
    if not pool and DEFAULT_CATEGORY:
        pool = QUIZ_BANK.get(DEFAULT_CATEGORY, {}).get(difficulty, [])
    if not pool:
        return None
    if excluded_indices:
        available = [q for idx, q in enumerate(pool) if idx not in excluded_indices]
    else:
        available = list(pool)
    if not available:
        return None
    return random.choice(available)


def create_quiz_board(category):
    """6x6のクイズボードを生成する"""
    board = []
    for y in range(6):
        row = []
        for x in range(6):
            difficulty = difficulty_for_cell(x, y)
            question = pick_question(category, difficulty)
            if question is None:
                question = pick_question(DEFAULT_CATEGORY, difficulty)
            row.append({
                "question": question["question"],
                "choices": question["choices"],
                "correct": question["answer"],
                "difficulty": difficulty,
                "removedChoices": [],
            })
        board.append(row)
    return board
