from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import json
import uuid
from othello_logic import get_flippable_disks, has_valid_moves, get_score
from quiz_data import create_quiz_board

app = FastAPI()

# マッチング待ちのプレイヤーをカテゴリ別に保持
waiting_players = {}

# 進行中のゲームルーム { room_id: { "players": [ws1, ws2], "board": [...], "turn": 1, "quiz_board": [...], "category": "..." } }
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
        choices = [
            {"index": idx, "label": text}
            for idx, text in enumerate(cell["choices"])
            if idx not in cell["removedChoices"]
        ]
        return {
            "type": "question_prompt",
            "x": x,
            "y": y,
            "question": cell["question"],
            "choices": choices,
            "difficulty": cell["difficulty"],
        }

    try:
        while True:
            data = await websocket.receive_text()
            payload = json.loads(data)
            action = payload.get("action")

            if action == "join_queue":
                category = payload.get("category", "一般常識")
                if category not in waiting_players:
                    waiting_players[category] = None
                if waiting_players[category] is None:
                    waiting_players[category] = websocket
                    await websocket.send_text(json.dumps({"type": "waiting", "category": category}))
                    continue

                room_id = str(uuid.uuid4())
                player1 = waiting_players[category]
                player2 = websocket
                waiting_players[category] = None

                quiz_board = create_quiz_board(category)
                room = {
                    "players": [player1, player2],
                    "board": create_initial_board(),
                    "quiz_board": quiz_board,
                    "category": category,
                    "turn": 1,
                    "pending": None,
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
                if room["board"][y][x] != 0:
                    continue

                flippable = get_flippable_disks(room["board"], x, y, color)
                if len(flippable) == 0:
                    await websocket.send_text(json.dumps({"type": "invalid_move", "message": "その場所には石を置けません。"}))
                    continue

                room["pending"] = {"player": color, "x": x, "y": y, "flippable": flippable}
                await websocket.send_text(json.dumps(build_question_prompt(room, x, y)))

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
                is_correct = selected_index == cell["correct"]

                if is_correct:
                    room["board"][y][x] = pending["player"]
                    for fx, fy in pending["flippable"]:
                        room["board"][fy][fx] = pending["player"]
                    message = "正解！石を置きました。"
                else:
                    if selected_index not in cell["removedChoices"]:
                        cell["removedChoices"].append(selected_index)
                    message = "不正解です。相手のターンになります。"

                next_turn = 2 if pending["player"] == 1 else 1
                game_over = False
                if not has_valid_moves(room["board"], next_turn):
                    if has_valid_moves(room["board"], pending["player"]):
                        message += " 相手は置けないため、あなたの番に戻ります。"
                        next_turn = pending["player"]
                    else:
                        game_over = True
                        message += " 盤面に置ける場所がありません。"
                if not any(0 in row for row in room["board"]):
                    game_over = True

                room["turn"] = next_turn
                room["pending"] = None
                score = get_score(room["board"])

                if game_over:
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
            if waiting == websocket:
                waiting_players[category] = None
                break
