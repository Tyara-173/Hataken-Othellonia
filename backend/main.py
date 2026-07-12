from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import json
import random
import uuid

try:
    from .othello_logic import get_flippable_disks, has_valid_moves, get_score, get_available_moves
    from .quiz_data import create_quiz_board
except ImportError:  # pragma: no cover - supports running from backend directory
    from othello_logic import get_flippable_disks, has_valid_moves, get_score, get_available_moves
    from quiz_data import create_quiz_board

app = FastAPI()

# CORSミドルウェアの設定
origins = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://hataken-othellonia-beta-4jmaknrsf-tyara1031-5481s-projects.vercel.app/"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# マッチング待ちのプレイヤーをカテゴリ別に保持
# 値は { "ws": WebSocket, "username": str } か None
waiting_players = {}

# 進行中のゲームルーム { room_id: { "players": [ws1, ws2], "board": [...], "turn": 1, "quiz_board": [...], "category": "...", "usernames": [name1, name2] } }
active_rooms = {}

def create_initial_board():
    return [
        [0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0],
        [0, 0, 1, 2, 0, 0],
        [0, 0, 2, 1, 0, 0],
        [0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0],
    ]

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    def build_question_prompt(room, x, y):
        cell = room["quiz_board"][y][x]
        available_indices = [idx for idx in range(len(cell["choices"])) if idx not in cell["removedChoices"]]
        if not available_indices:
            available_indices = list(range(len(cell["choices"])))

        shuffled_indices = available_indices[:]
        random.shuffle(shuffled_indices)

        display_choices = []
        choice_map = {}
        for display_index, original_index in enumerate(shuffled_indices):
            choice_map[display_index] = original_index
            display_choices.append({
                "index": display_index,
                "label": cell["choices"][original_index],
            })

        correct_display_index = next(
            (display_index for display_index, original_index in choice_map.items() if original_index == cell["correct"]),
            None,
        )

        return {
            "type": "question_prompt",
            "x": x,
            "y": y,
            "question": cell["question"],
            "choices": display_choices,
            "difficulty": cell["difficulty"],
        }, choice_map, correct_display_index

    try:
        while True:
            data = await websocket.receive_text()
            payload = json.loads(data)
            action = payload.get("action")

            if action == "join_queue":
                category = payload.get("category", "一般常識")
                username = payload.get("username", "名無し") or "名無し"
                if category not in waiting_players:
                    waiting_players[category] = None
                if waiting_players[category] is None:
                    waiting_players[category] = {"ws": websocket, "username": username}
                    await websocket.send_text(json.dumps({"type": "waiting", "category": category}))
                    continue

                room_id = str(uuid.uuid4())
                player1 = waiting_players[category]["ws"]
                player2 = websocket
                player1_name = waiting_players[category]["username"]
                player2_name = username
                waiting_players[category] = None

                quiz_board = create_quiz_board(category)
                room = {
                    "players": [player1, player2],
                    "usernames": [player1_name, player2_name],
                    "board": create_initial_board(),
                    "quiz_board": quiz_board,
                    "category": category,
                    "turn": 1,
                    "pending": None,
                    "wrong_count": 0,
                    "attempted_positions": [],
                }
                active_rooms[room_id] = room

                for idx, player in enumerate(room["players"], start=1):
                    await player.send_text(json.dumps({
                        "type": "start",
                        "room_id": room_id,
                        "color": idx,
                        "board": room["board"],
                        "turn": 1,
                        "category": category,
                        "quiz_board": quiz_board,
                        "player_names": {"1": room["usernames"][0], "2": room["usernames"][1]},
                        "available_moves": get_available_moves(room["board"], room["turn"]),
                    }))

            elif action == "click_cell":
                room_id = payload.get("room_id")
                room = active_rooms.get(room_id)
                if not room:
                    continue
                if room["pending"] is not None:
                    continue

                color = payload.get("color")
                x, y = payload.get("x"), payload.get("y")
                if room["turn"] != color:
                    continue
                if not (0 <= x < 6 and 0 <= y < 6):
                    continue

                if not has_valid_moves(room["board"], color, room["attempted_positions"]):
                    next_turn = 2 if color == 1 else 1
                    game_over = False
                    message = "置ける場所がないためパスします。"
                    if not has_valid_moves(room["board"], next_turn):
                        game_over = True
                        message += " 盤面に置ける場所がありません。"
                    room["turn"] = next_turn
                    room["wrong_count"] = 0
                    room["attempted_positions"] = []
                    score = get_score(room["board"])
                    update_msg = json.dumps({
                        "type": "update",
                        "board": room["board"],
                        "turn": room["turn"],
                        "score": score,
                        "message": message,
                        "game_over": game_over,
                        "available_moves": get_available_moves(room["board"], room["turn"]),
                    })
                    for p in room["players"]:
                        await p.send_text(update_msg)
                    continue

                if room["board"][y][x] != 0:
                    continue
                if (x, y) in room["attempted_positions"]:
                    await websocket.send_text(json.dumps({"type": "invalid_move", "message": "この場所はこのターン中にすでに選択しました。別の場所を選んでください。"}))
                    continue

                flippable = get_flippable_disks(room["board"], x, y, color)
                if len(flippable) == 0:
                    await websocket.send_text(json.dumps({"type": "invalid_move", "message": "その場所には石を置けません。"}))
                    continue

                prompt_payload, choice_map, correct_display_index = build_question_prompt(room, x, y)
                room["pending"] = {
                    "player": color,
                    "x": x,
                    "y": y,
                    "flippable": flippable,
                    "choice_map": choice_map,
                    "correct_display_index": correct_display_index,
                }
                await websocket.send_text(json.dumps(prompt_payload))

            elif action == "answer_question":
                room_id = payload.get("room_id")
                room = active_rooms.get(room_id)
                if not room or room["pending"] is None:
                    continue

                selected_index = payload.get("selected_index")
                pending = room["pending"]
                if pending["player"] != payload.get("color"):
                    continue

                x, y = pending["x"], pending["y"]
                cell = room["quiz_board"][y][x]
                choice_map = pending.get("choice_map", {})
                correct_display_index = pending.get("correct_display_index")

                if isinstance(choice_map, dict) and selected_index in choice_map:
                    selected_original_index = choice_map[selected_index]
                else:
                    selected_original_index = None

                is_correct = selected_original_index is not None and selected_original_index == cell["correct"]
                if selected_original_index is None and correct_display_index is not None:
                    is_correct = selected_index == correct_display_index

                current_player = pending["player"]
                opponent = 2 if current_player == 1 else 1
                game_over = False

                if is_correct:
                    room["board"][y][x] = current_player
                    for fx, fy in pending["flippable"]:
                        room["board"][fy][fx] = current_player
                    room["wrong_count"] = 0
                    room["attempted_positions"] = []
                    message = "正解！石を置きました。"
                    next_turn = opponent

                    if not has_valid_moves(room["board"], next_turn):
                        if has_valid_moves(room["board"], current_player):
                            message += " 相手は置けないため、あなたの番に戻ります。"
                            next_turn = current_player
                        else:
                            game_over = True
                            message += " 盤面に置ける場所がありません。"
                else:
                    if selected_original_index is not None and selected_original_index not in cell["removedChoices"]:
                        cell["removedChoices"].append(selected_original_index)
                    room["wrong_count"] += 1
                    room["attempted_positions"].append((x, y))

                    remaining_moves = has_valid_moves(room["board"], current_player, room["attempted_positions"])
                    if room["wrong_count"] >= 3 or not remaining_moves:
                        message = "不正解です。"
                        if room["wrong_count"] >= 3:
                            message += " 3回間違えたためパスします。"
                        else:
                            message += " 置ける場所がなくなったためパスします。"
                        next_turn = opponent

                        if not has_valid_moves(room["board"], next_turn):
                            if has_valid_moves(room["board"], current_player):
                                message += " 相手は置けないため、あなたの番に戻ります。"
                                next_turn = current_player
                            else:
                                game_over = True
                                message += " 盤面に置ける場所がありません。"

                        room["wrong_count"] = 0
                        room["attempted_positions"] = []
                    else:
                        next_turn = current_player
                        message = f"不正解です。同じ場所は選べません。別の場所を選んでください。残りあと{3 - room['wrong_count']}回間違えられます。"

                room["turn"] = next_turn
                room["pending"] = None
                score = get_score(room["board"])

                if not any(0 in row for row in room["board"]) and not game_over:
                    game_over = True
                    if score["black"] > score["white"]:
                        message += f" 黒の勝ち！ ({score['black']} 対 {score['white']})"
                    elif score["white"] > score["black"]:
                        message += f" 白の勝ち！ ({score['white']} 対 {score['black']})"
                    else:
                        message += f" 引き分け！ ({score['black']} 対 {score['white']})"

                if game_over and "勝ち" not in message and "引き分け" not in message:
                    if score["black"] > score["white"]:
                        message += f" 黒の勝ち！ ({score['black']} 対 {score['white']})"
                    elif score["white"] > score["black"]:
                        message += f" 白の勝ち！ ({score['white']} 対 {score['black']})"
                    else:
                        message += f" 引き分け！ ({score['black']} 対 {score['white']})"

                update_msg = json.dumps({
                    "type": "update",
                    "board": room["board"],
                    "turn": room["turn"],
                    "score": score,
                    "message": message,
                    "game_over": game_over,
                    "available_moves": get_available_moves(room["board"], room["turn"]),
                })
                for p in room["players"]:
                    await p.send_text(update_msg)

            elif action == "request_question":
                room_id = payload.get("room_id")
                room = active_rooms.get(room_id)
                if not room:
                    continue
                x, y = payload.get("x"), payload.get("y")
                cell = room["quiz_board"][y][x]
                await websocket.send_text(json.dumps(build_question_prompt(room, x, y)))

    except WebSocketDisconnect:
        for category, waiting in list(waiting_players.items()):
            if waiting and waiting.get("ws") == websocket:
                waiting_players[category] = None
                break
