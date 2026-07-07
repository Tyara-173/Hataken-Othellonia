// WebSocketでバックエンドに接続
const ws = new WebSocket("ws://localhost:8000/ws");

ws.onopen = () => {
    console.log("WebSocket接続成功！");
};

ws.onmessage = (event) => {
    const gameState = JSON.parse(event.data);
    renderBoard(gameState);
};

function renderBoard(gameState) {
    const boardDiv = document.getElementById("board");
    const statusDiv = document.getElementById("status");
    
    // ターンの表示を更新
    statusDiv.textContent = `現在のターン: ${gameState.turn}`;
    boardDiv.innerHTML = ""; // 盤面をリセット

    // 6x6の盤面を描画
    for (let y = 0; y < 6; y++) {
        for (let x = 0; x < 6; x++) {
            const cellValue = gameState.board[y][x];
            
            const cellDiv = document.createElement("div");
            cellDiv.className = "cell";
            
            // 石を描画
            if (cellValue === 1 || cellValue === 2) {
                const diskDiv = document.createElement("div");
                diskDiv.className = "disk " + (cellValue === 1 ? "black" : "white");
                cellDiv.appendChild(diskDiv);
            }

            // クリック時の処理
            cellDiv.onclick = () => {
                const playerId = document.getElementById("playerId").value;
                const payload = {
                    action: "click_cell",
                    x: x,
                    y: y,
                    player_id: playerId
                };
                ws.send(JSON.stringify(payload));
            };

            boardDiv.appendChild(cellDiv);
        }
    }
}