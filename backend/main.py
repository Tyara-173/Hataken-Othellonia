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

    try:
        while True:
            data = await websocket.receive_text()
            payload = json.loads(data)

            if payload["action"] == "join_queue":
                category = payload.get("category", "一般常識")
                if category not in waiting_players:
                    waiting_players[category] = None
                if waiting_players[category] is None:
                    waiting_players[category] = websocket
                    await websocket.send_text(json.dumps({"type": "waiting", "category": category}))
                    continue

                # 同じカテゴリの待機プレイヤーとマッチング
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
                }
                active_rooms[room_id] = room

                await player1.send_text(json.dumps({
                    "type": "start",
                    "room_id": room_id,
                    "color": 1,
                    "board": room["board"],
                    "turn": 1,
                    "category": category,
                    "quiz_board": quiz_board,
                }))
                await player2.send_text(json.dumps({
                    "type": "start",
                    "room_id": room_id,
                    "color": 2,
                    "board": room["board"],
                    "turn": 1,
                    "category": category,
                    "quiz_board": quiz_board,
                }))

            elif payload["action"] == "click_cell":
                room_id = payload["room_id"]
                room = active_rooms.get(room_id)
                if not room:
                    continue

                color = payload["color"]
                x, y = payload["x"], payload["y"]

                if room["turn"] != color:
                    continue

                flippable = get_flippable_disks(room["board"], x, y, color)
                if len(flippable) > 0:
                    room["board"][y][x] = color
                    for fx, fy in flippable:
                        room["board"][fy][fx] = color

                    next_turn = 2 if color == 1 else 1
                    message = ""
                    game_over = False

                    if not has_valid_moves(room["board"], next_turn):
                        if not has_valid_moves(room["board"], color):
                            game_over = True
                            message = "お互いに置ける場所がありません。"
                        else:
                            pass_color = "白" if next_turn == 2 else "黒"
                            message = f"{pass_color}は置ける場所がないためパスされました！"
                            next_turn = color

                    if not any(0 in row for row in room["board"]):
                        game_over = True

                    room["turn"] = next_turn
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
    except WebSocketDisconnect:
        for category, waiting in list(waiting_players.items()):
            if waiting == websocket:
                waiting_players[category] = None
                break

    try:
        while True:
            data = await websocket.receive_text()
            payload = json.loads(data)
            
            if payload["action"] == "click_cell":
                room_id = payload["room_id"]
                room = active_rooms.get(room_id)
                if not room: continue

                color = payload["color"]
                x, y = payload["x"], payload["y"]

                # 自分のターンかチェック
                if room["turn"] != color:
                    continue

                # オセロの判定
                flippable = get_flippable_disks(room["board"], x, y, color)
                if len(flippable) > 0:
                    # 石を置いて、挟んだ石を裏返す
                    room["board"][y][x] = color
                    for fx, fy in flippable:
                        room["board"][fy][fx] = color
                    
                    # ターン交代の準備
                    next_turn = 2 if color == 1 else 1
                    message = ""
                    game_over = False
                    
                    # --- パスとゲーム終了の判定 ---
                    if not has_valid_moves(room["board"], next_turn):
                        # 次のプレイヤーが置けない場合
                        if not has_valid_moves(room["board"], color):
                            # 両方とも置けない -> ゲーム終了
                            game_over = True
                            message = "お互いに置ける場所がありません。"
                        else:
                            # 相手だけ置けない -> パスして自分のターン継続
                            pass_color = "白" if next_turn == 2 else "黒"
                            message = f"{pass_color}は置ける場所がないためパスされました！"
                            next_turn = color # ターンを戻す
                    
                    # 盤面が全て埋まった場合もゲーム終了
                    if not any(0 in row for row in room["board"]):
                        game_over = True
                        
                    room["turn"] = next_turn
                    score = get_score(room["board"])

                    # 最終結果のメッセージ作成
                    if game_over:
                        if score["black"] > score["white"]:
                            message += f" 黒の勝ち！ ({score['black']} 対 {score['white']})"
                        elif score["white"] > score["black"]:
                            message += f" 白の勝ち！ ({score['white']} 対 {score['black']})"
                        else:
                            message += f" 引き分け！ ({score['black']} 対 {score['white']})"

                    # 両プレイヤーに盤面と状態を同期
                    update_msg = json.dumps({
                        "type": "update", 
                        "board": room["board"], 
                        "turn": room["turn"],
                        "score": score,
                        "message": message,
                        "game_over": game_over
                    })
                    for p in room["players"]:
                        await p.send_text(update_msg)
    except WebSocketDisconnect:
        # どちらかが切断した時の処理（今回は簡易的に待合室のクリアのみ）
        if waiting_player == websocket:
            waiting_player = None