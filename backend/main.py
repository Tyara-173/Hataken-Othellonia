# main.py
from fastapi import FastAPI, WebSocket
import json
from othello_logic import get_flippable_disks

app = FastAPI()

# 6x6の初期盤面 (1: p1/黒, 2: p2/白)
initial_board = [
    [0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0],
    [0, 0, 1, 2, 0, 0],
    [0, 0, 2, 1, 0, 0],
    [0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0],
]

game_state = {
    "turn": "p1", # p1が黒(1)、p2が白(2)とする
    "board": initial_board
}

clients = []

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    clients.append(websocket)
    await websocket.send_text(json.dumps(game_state))
    
    try:
        while True:
            data = await websocket.receive_text()
            payload = json.loads(data)
            
            if payload["action"] == "click_cell":
                # どっちのプレイヤーの操作か判定
                current_player_num = 1 if game_state["turn"] == "p1" else 2
                req_player = 1 if payload["player_id"] == "p1" else 2

                # 自分のターンじゃないのに送ってきたら無視
                if current_player_num != req_player:
                    continue

                x, y = payload["x"], payload["y"]
                
                # ひっくり返せる石を取得
                flippable = get_flippable_disks(game_state["board"], x, y, current_player_num)
                
                # 置ける場合のみ処理を実行
                if len(flippable) > 0:
                    # 石を置く
                    game_state["board"][y][x] = current_player_num
                    # 挟んだ石を裏返す
                    for fx, fy in flippable:
                        game_state["board"][fy][fx] = current_player_num
                    
                    # ターン交代
                    game_state["turn"] = "p2" if game_state["turn"] == "p1" else "p1"
                    
                    # 更新された盤面を全員に送信
                    for client in clients:
                        await client.send_text(json.dumps(game_state))
                        
    except Exception:
        clients.remove(websocket)