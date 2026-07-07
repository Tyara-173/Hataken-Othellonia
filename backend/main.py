from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import json
import uuid
from othello_logic import get_flippable_disks # 前回作ったオセロロジック

app = FastAPI()

# マッチング待ちのプレイヤー
waiting_player = None

# 進行中のゲームルーム { room_id: { "players": [ws1, ws2], "board": [...], "turn": 1 } }
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
    global waiting_player
    await websocket.accept()

    # --- マッチング処理 ---
    if waiting_player is None:
        # 待っている人がいなければ、自分が待つ
        waiting_player = websocket
        await websocket.send_text(json.dumps({"type": "waiting"}))
    else:
        # 待っている人がいれば、マッチング成立！
        room_id = str(uuid.uuid4())
        player1 = waiting_player
        player2 = websocket
        waiting_player = None # 待合室を空にする

        # ルームを作成
        active_rooms[room_id] = {
            "players": [player1, player2],
            "board": create_initial_board(),
            "turn": 1 # 1: 黒(p1), 2: 白(p2)
        }

        # プレイヤー1(黒)に開始通知
        await player1.send_text(json.dumps({
            "type": "start", "room_id": room_id, "color": 1, "board": active_rooms[room_id]["board"], "turn": 1
        }))
        # プレイヤー2(白)に開始通知
        await player2.send_text(json.dumps({
            "type": "start", "room_id": room_id, "color": 2, "board": active_rooms[room_id]["board"], "turn": 1
        }))

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
                    room["board"][y][x] = color
                    for fx, fy in flippable:
                        room["board"][fy][fx] = color
                    
                    # ターン交代
                    room["turn"] = 2 if color == 1 else 1
                    
                    # 両プレイヤーに盤面を同期
                    update_msg = json.dumps({"type": "update", "board": room["board"], "turn": room["turn"]})
                    for p in room["players"]:
                        await p.send_text(update_msg)

    except WebSocketDisconnect:
        # どちらかが切断した時の処理（今回は簡易的に待合室のクリアのみ）
        if waiting_player == websocket:
            waiting_player = None