from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import json
import random
import uuid

try:
    from .othello_logic import get_flippable_disks, has_valid_moves, get_score, get_available_moves
    from .quiz_data import create_quiz_board, get_available_categories
except ImportError:  # pragma: no cover - supports running from backend directory
    from othello_logic import get_flippable_disks, has_valid_moves, get_score, get_available_moves
    from quiz_data import create_quiz_board, get_available_categories

app = FastAPI()

# CORSミドルウェアの設定
origins = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://hataken-othellonia-beta-4jmaknrsf-tyara1031-5481s-projects.vercel.app",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/categories")
def list_categories():
    return {"categories": get_available_categories()}


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


def build_surrender_payload(room, surrendering_color):
    winner_color = 2 if surrendering_color == 1 else 1
    score = get_score(room["board"])
    surrendering_label = "黒" if surrendering_color == 1 else "白"
    winner_label = "白" if winner_color == 2 else "黒"
    return {
        "type": "update",
        "board": room["board"],
        "turn": winner_color,
        "score": score,
        "message": f"{surrendering_label}が降参しました。{winner_label}の勝ちです。",
        "game_over": True,
        "available_moves": [],
    }


@app.websocket("/ws/{room_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str):
    await websocket.accept()

    async def notify_room_disconnect(disconnected_ws):
        room = active_rooms.get(room_id)
        if not room:
            return

        remaining_players = [player for player in room["players"] if player is not disconnected_ws]
        if remaining_players:
            # 相手に切断を通知
            for player in remaining_players:
                try:
                    await player.send_text(json.dumps({
                        "type": "opponent_disconnected",
                        "message": "相手プレイヤーが切断されたため、対戦を終了します。",
                    }))
                except Exception:
                    pass
        
        # 部屋を削除
        active_rooms.pop(room_id, None)

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

            if action == "join_room":
                category = payload.get("category", "雑学")
                username = payload.get("username", "名無し") or "名無し"
                player_id = payload.get("player_id")

                if room_id not in active_rooms:
                    # 新しい部屋を作成
                    quiz_board = create_quiz_board(category)
                    room = {
                        "players": [websocket],
                        "usernames": [username],
                        "player_ids": [player_id],
                        "board": create_initial_board(),
                        "quiz_board": quiz_board,
                        "category": category,
                        "turn": 1,
                        "pending": None,
                        "wrong_count": 0,
                        "attempted_positions": [],
                    }
                    active_rooms[room_id] = room
                    await websocket.send_text(json.dumps({
                        "type": "waiting",
                        "message": "対戦相手を待っています...",
                        "room_id": room_id,
                    }))
                else:
                    # 既存の部屋に参加
                    room = active_rooms[room_id]
                    if len(room["players"]) == 1:
                        room["players"].append(websocket)
                        room["usernames"].append(username)
                        room["player_ids"].append(player_id)

                        # ゲーム開始を両プレイヤーに通知
                        for idx, player in enumerate(room["players"], start=1):
                            await player.send_text(json.dumps({
                                "type": "start",
                                "room_id": room_id,
                                "color": idx,
                                "board": room["board"],
                                "turn": 1,
                                "category": room["category"],
                                "player_names": {"1": room["usernames"][0], "2": room["usernames"][1]},
                                "player_id": room["player_ids"][idx-1],
                                "available_moves": get_available_moves(room["board"], 1),
                            }))
                    else:
                        # 部屋が満員の場合
                        await websocket.send_text(json.dumps({
                            "type": "error",
                            "message": "この部屋は満員です。",
                        }))

            elif action == "click_cell":
                room = active_rooms.get(room_id)
                if not room or room.get("pending"):
                    continue

                color = payload.get("color")
                pid = payload.get("player_id")
                x, y = payload.get("x"), payload.get("y")

                # プレイヤーのIDとターンが一致するか確認
                try:
                    player_index = room["player_ids"].index(pid)
                    if player_index + 1 != color or room["turn"] != color:
                        continue
                except (ValueError, IndexError):
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
                if not flippable:
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
                room = active_rooms.get(room_id)
                if not room or not room.get("pending"):
                    continue

                selected_index = payload.get("selected_index")
                pending = room["pending"]
                pid = payload.get("player_id")

                try:
                    player_index = room["player_ids"].index(pid)
                    if player_index + 1 != pending["player"]:
                        continue
                except (ValueError, IndexError):
                    continue

                x, y = pending["x"], pending["y"]
                cell = room["quiz_board"][y][x]
                choice_map = pending.get("choice_map", {})
                correct_display_index = pending.get("correct_display_index")

                selected_original_index = choice_map.get(selected_index)
                is_correct = selected_original_index is not None and selected_original_index == cell["correct"]

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
                
                if game_over:
                    s_b, s_w = score["black"], score["white"]
                    if s_b > s_w:
                        message += f" 黒の勝ち！ ({s_b} 対 {s_w})"
                    elif s_w > s_b:
                        message += f" 白の勝ち！ ({s_w} 対 {s_b})"
                    else:
                        message += f" 引き分け！ ({s_b} 対 {s_b})"

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

            elif action == "surrender":
                room = active_rooms.get(room_id)
                if not room:
                    continue

                pid = payload.get("player_id")
                try:
                    player_index = room["player_ids"].index(pid)
                    color = player_index + 1
                except (ValueError, IndexError):
                    continue

                room["pending"] = None
                room["attempted_positions"] = []
                room["wrong_count"] = 0
                update_msg = json.dumps(build_surrender_payload(room, color))
                for p in room["players"]:
                    await p.send_text(update_msg)

    except WebSocketDisconnect:
        await notify_room_disconnect(websocket)
