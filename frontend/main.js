// ゲームのセッション情報
let ws = null;
let myRoomId = null;
let myColor = null; // 1:黒, 2:白

// 画面の切り替え関数
function showScreen(screenId) {
    document.querySelectorAll('.screen').forEach(el => el.classList.remove('active'));
    document.getElementById(screenId).classList.add('active');
}

// 「オンライン対戦を探す」ボタンを押した時の処理
document.getElementById('matchBtn').addEventListener('click', () => {
    showScreen('waitingScreen');
    
    // ここでWebSocketに接続
    ws = new WebSocket("ws://localhost:8000/ws");
    
    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        
        if (data.type === "waiting") {
            // 待機中のまま（UI変更なし）
            console.log("対戦相手を待っています...");
        } 
        else if (data.type === "start") {
            // マッチング成立！ゲーム画面へ
            myRoomId = data.room_id;
            myColor = data.color;
            showScreen('gameScreen');
            
            const colorName = myColor === 1 ? "黒 (先手)" : "白 (後手)";
            document.getElementById('myColor').textContent = `あなたは: ${colorName}`;
            
            renderBoard(data.board, data.turn);
        }
        else if (data.type === "update") {
            // 盤面の更新
            renderBoard(data.board, data.turn);
        }
    };
});

// 盤面の描画関数
function renderBoard(board, currentTurn) {
    const boardDiv = document.getElementById("board");
    const statusDiv = document.getElementById("status");
    
    // ターンの表示
    const turnName = currentTurn === 1 ? "黒" : "白";
    statusDiv.textContent = `現在のターン: ${turnName}`;
    
    // 自分のターンの時は色を変えるなどの演出
    if (currentTurn === myColor) {
        statusDiv.style.color = "#d32f2f"; // 赤色でアピール
        statusDiv.textContent += " (あなたの番です！)";
    } else {
        statusDiv.style.color = "#333";
    }

    boardDiv.innerHTML = ""; // リセット

    for (let y = 0; y < 6; y++) {
        for (let x = 0; x < 6; x++) {
            const cellValue = board[y][x];
            const cellDiv = document.createElement("div");
            cellDiv.className = "cell";
            
            if (cellValue === 1 || cellValue === 2) {
                const diskDiv = document.createElement("div");
                diskDiv.className = "disk " + (cellValue === 1 ? "black" : "white");
                cellDiv.appendChild(diskDiv);
            }

            // クリックでサーバーに送信
            cellDiv.onclick = () => {
                // 自分のターンでない時は無視
                if (currentTurn !== myColor) return;

                const payload = {
                    action: "click_cell",
                    room_id: myRoomId,
                    color: myColor,
                    x: x,
                    y: y
                };
                ws.send(JSON.stringify(payload));
            };
            boardDiv.appendChild(cellDiv);
        }
    }
}