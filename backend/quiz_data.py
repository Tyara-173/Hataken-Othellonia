import random

# カテゴリと難易度ごとの固定問題プール
QUIZ_BANK = {
    "漢字": {
        "easy": [
            {
                "question": "次の漢字の読み方は？「海」",
                "choices": ["うみ", "かわ", "やま", "そら"],
                "answer": 0,
            },
            {
                "question": "次の漢字の読み方は？「雨」",
                "choices": ["あめ", "ゆき", "かぜ", "ひ"],
                "answer": 0,
            },
        ],
        "normal": [
            {
                "question": "次の漢字の読み方は？「森」",
                "choices": ["もり", "はやし", "いけ", "たに"],
                "answer": 0,
            },
            {
                "question": "次の漢字の読み方は？「知」",
                "choices": ["しる", "つね", "ただ", "さと"],
                "answer": 3,
            },
        ],
        "hard": [
            {
                "question": "次の漢字の読み方は？「瑠璃」",
                "choices": ["るり", "りゅう", "るい", "らり"],
                "answer": 0,
            },
            {
                "question": "次の漢字の読み方は？「漸進」",
                "choices": ["ぜんしん", "しんしん", "ぜんしん", "じんしん"],
                "answer": 0,
            },
        ],
    },
    "一般常識": {
        "easy": [
            {
                "question": "1年は何日ですか？",
                "choices": ["365日", "360日", "364日", "366日"],
                "answer": 0,
            },
            {
                "question": "太陽は何色に見えますか？",
                "choices": ["黄色", "赤色", "青色", "緑色"],
                "answer": 0,
            },
        ],
        "normal": [
            {
                "question": "日本の首都はどこですか？",
                "choices": ["東京", "大阪", "名古屋", "京都"],
                "answer": 0,
            },
            {
                "question": "1kgは何gですか？",
                "choices": ["1000g", "100g", "10g", "10000g"],
                "answer": 0,
            },
        ],
        "hard": [
            {
                "question": "日本の法律で成人年齢は何歳ですか？",
                "choices": ["18歳", "20歳", "16歳", "21歳"],
                "answer": 0,
            },
            {
                "question": "日本の国旗の正式名称は？",
                "choices": ["日章旗", "日之丸", "旭日旗", "朝日旗"],
                "answer": 0,
            },
        ],
    },
    "雑学": {
        "easy": [
            {
                "question": "世界で最も高い山は？",
                "choices": ["エベレスト", "富士山", "キリマンジャロ", "マッキンリー"],
                "answer": 0,
            },
            {
                "question": "ネコの鳴き声は？",
                "choices": ["にゃー", "わん", "ぶー", "チュー"],
                "answer": 0,
            },
        ],
        "normal": [
            {
                "question": "コーヒーの実は何色？",
                "choices": ["赤", "青", "白", "黒"],
                "answer": 0,
            },
            {
                "question": "地球の表面の約何％が海？",
                "choices": ["70%", "50%", "30%", "90%"],
                "answer": 0,
            },
        ],
        "hard": [
            {
                "question": "蜂の仲間で女王バチはどれ？",
                "choices": ["女王蜂", "働き蜂", "雄蜂", "皇蜂"],
                "answer": 0,
            },
            {
                "question": "ワインの製造に使う果物は？",
                "choices": ["ぶどう", "りんご", "もも", "いちご"],
                "answer": 0,
            },
        ],
    },
    "地理": {
        "easy": [
            {
                "question": "日本の首都は？",
                "choices": ["東京", "大阪", "札幌", "福岡"],
                "answer": 0,
            },
            {
                "question": "北海道は日本のどこ？",
                "choices": ["北", "南", "東", "西"],
                "answer": 0,
            },
        ],
        "normal": [
            {
                "question": "富士山は何県にありますか？",
                "choices": ["静岡県", "東京都", "長野県", "神奈川県"],
                "answer": 0,
            },
            {
                "question": "日本で最も長い川は？",
                "choices": ["信濃川", "利根川", "荒川", "淀川"],
                "answer": 0,
            },
        ],
        "hard": [
            {
                "question": "世界で最も広い大陸は？",
                "choices": ["アジア", "アフリカ", "北アメリカ", "南アメリカ"],
                "answer": 0,
            },
            {
                "question": "エジプトの首都は？",
                "choices": ["カイロ", "アレキサンドリア", "ルクソール", "ギザ"],
                "answer": 0,
            },
        ],
    },
}

DEFAULT_CATEGORY = "一般常識"
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
    pool = QUIZ_BANK.get(category, QUIZ_BANK[DEFAULT_CATEGORY]).get(difficulty, [])
    if not pool:
        pool = QUIZ_BANK[DEFAULT_CATEGORY].get(difficulty, [])
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
