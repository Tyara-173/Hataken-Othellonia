'use client';

import { useEffect, useRef, useState } from 'react';

const BOARD_SIZE = 6;

function createInitialBoard() {
  return [
    [0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0],
    [0, 0, 1, 2, 0, 0],
    [0, 0, 2, 1, 0, 0],
    [0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0],
  ];
}

function getTurnLabel(turn) {
  return turn === 1 ? '黒' : '白';
}

function getColorLabel(color) {
  return color === 1 ? '黒 (先手)' : '白 (後手)';
}

export default function HomePage() {
  const [screen, setScreen] = useState('title');
  const [username, setUsername] = useState('');
  const [category, setCategory] = useState('漢字');
  const [message, setMessage] = useState('');
  const [playerNames, setPlayerNames] = useState({ 1: '-', 2: '-' });
  const [myColor, setMyColor] = useState(null);
  const [roomId, setRoomId] = useState(null);
  const [board, setBoard] = useState(createInitialBoard());
  const [currentTurn, setCurrentTurn] = useState(1);
  const [availableMoves, setAvailableMoves] = useState([]);
  const [question, setQuestion] = useState(null);
  const [statusText, setStatusText] = useState('現在のターン: -');
  const [connectionError, setConnectionError] = useState('');

  const wsRef = useRef(null);
  const roomRef = useRef(null);
  const colorRef = useRef(null);

  useEffect(() => {
    return () => {
      if (wsRef.current && wsRef.current.readyState === 1) {
        wsRef.current.close();
      }
    };
  }, []);

  const returnToTitleWithConfirm = (message) => {
    const shouldReturn = window.confirm(`${message}\nOKを押すとタイトルに戻ります。`);
    if (!shouldReturn) {
      return;
    }

    setScreen('title');
    setConnectionError(message);
    setMessage('');
    setQuestion(null);
    setBoard(createInitialBoard());
    setCurrentTurn(1);
    setAvailableMoves([]);
    setStatusText('現在のターン: -');
    setRoomId(null);
    roomRef.current = null;
    setMyColor(null);
    colorRef.current = null;
    setPlayerNames({ 1: '-', 2: '-' });
  };

  const startMatch = () => {
    const ws = new WebSocket('wss://othello-backend-qrhzeh4tlq-an.a.run.app/ws');

    setScreen('waiting');
    setQuestion(null);
    setMessage('');
    setConnectionError('');
    setBoard(createInitialBoard());
    setCurrentTurn(1);
    setAvailableMoves([]);
    setStatusText('現在のターン: -');

    ws.onopen = () => {
      ws.send(JSON.stringify({
        action: 'join_queue',
        category,
        username: username.trim() || '名無し',
      }));
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);

      if (data.type === 'waiting') {
        setMessage(`ジャンル「${data.category}」の対戦相手を待っています...`);
      } else if (data.type === 'start') {
        setRoomId(data.room_id);
        roomRef.current = data.room_id;
        setMyColor(data.color);
        colorRef.current = data.color;
        setPlayerNames(data.player_names || { 1: '-', 2: '-' });
        setBoard(data.board || createInitialBoard());
        setCurrentTurn(data.turn || 1);
        setAvailableMoves(data.available_moves || []);
        setQuestion(null);
        setScreen('game');
        setStatusText(`現在のターン: ${getTurnLabel(data.turn)}`);
        setMessage('問題をクリックして回答してください。');
      } else if (data.type === 'question_prompt') {
        setQuestion(data);
        setMessage('');
      } else if (data.type === 'update') {
        setBoard(data.board || createInitialBoard());
        setCurrentTurn(data.turn || 1);
        setAvailableMoves(data.available_moves || []);
        setQuestion(null);
        setStatusText(`現在のターン: ${getTurnLabel(data.turn || 1)}`);
        if (data.message) {
          setMessage(data.message);
        }
      } else if (data.type === 'invalid_move') {
        setMessage(data.message || 'その手は無効です。');
      } else if (data.type === 'opponent_disconnected') {
        returnToTitleWithConfirm(data.message || '通信が切断されました。対戦を終了します。');
      }
    };

    ws.onerror = () => {
      returnToTitleWithConfirm('接続エラーが発生しました。バックエンドが起動しているか確認してください。');
    };

    ws.onclose = () => {
      if (wsRef.current !== ws) {
        return;
      }

      returnToTitleWithConfirm('通信が切断されました。対戦を終了します。');
    };

    wsRef.current = ws;
  };

  const handleCellClick = (x, y) => {
    if (!wsRef.current || currentTurn !== myColor || !roomRef.current || !colorRef.current) {
      return;
    }

    wsRef.current.send(JSON.stringify({
      action: 'click_cell',
      room_id: roomRef.current,
      color: colorRef.current,
      x,
      y,
    }));
  };

  const handleAnswer = (choice) => {
    if (!wsRef.current || !roomRef.current || !colorRef.current) {
      return;
    }

    wsRef.current.send(JSON.stringify({
      action: 'answer_question',
      room_id: roomRef.current,
      color: colorRef.current,
      selected_index: choice.index,
    }));
  };

  const isMyTurn = currentTurn === myColor;

  return (
    <main>
      {screen === 'title' && (
        <section className="screen">
          <div className="title-box">
            <h1>はたけんオセロニア</h1>
            <div className="input-group">
              <label htmlFor="username">プレイヤー名</label>
              <input
                id="username"
                value={username}
                onChange={(event) => setUsername(event.target.value)}
                placeholder="名前を入力してください"
              />
            </div>
            {/* {connectionError ? <div className="error-text">{connectionError}</div> : null} */}
            <button className="match-btn" onClick={() => setScreen('category')}>
              オンライン対戦を探す
            </button>
          </div>
        </section>
      )}

      {screen === 'category' && (
        <section className="screen">
          <div className="title-box">
            <h2>クイズジャンルを選択</h2>
            <div className="input-group">
              <label htmlFor="category">ジャンル</label>
              <select id="category" value={category} onChange={(event) => setCategory(event.target.value)}>
                <option value="漢字">漢字</option>
                <option value="地理">地理</option>
              </select>
            </div>
            <button className="match-btn" onClick={startMatch}>
              対戦を開始
            </button>
          </div>
        </section>
      )}

      {screen === 'waiting' && (
        <section className="screen">
          <div className="title-box">
            <h2>対戦相手を探しています...</h2>
            <p>{message || '少々お待ちください ⏳'}</p>
          </div>
        </section>
      )}

      {screen === 'game' && (
        <section className="screen">
          <div className="info-panel">
            <div>プレイヤー: 先手 {playerNames[1]} / 後手 {playerNames[2]}</div>
            <div style={{ marginTop: 6 }}>
              あなたは: {myColor ? getColorLabel(myColor) : '-'}
            </div>
            <div className="status-text" style={{ color: isMyTurn ? '#dc2626' : '#1f2937' }}>
              {statusText}{isMyTurn ? ' (あなたの番です！)' : ''}
            </div>
            <div className="message-text">{message}</div>
            {connectionError ? <div className="error-text">{connectionError}</div> : null}
          </div>

          {question ? (
            <div className="question-panel">
              <div className="difficulty-tag">難易度: {question.difficulty}</div>
              <div className="question-text">{question.question}</div>
              <div className="choices-container">
                {question.choices.map((choice) => (
                  <button key={`${choice.index}-${choice.label}`} className="choice-btn" onClick={() => handleAnswer(choice)}>
                    {choice.label}
                  </button>
                ))}
              </div>
            </div>
          ) : null}

          <div className="board" role="grid" aria-label="オセロ盤">
            {board.map((row, y) =>
              row.map((cellValue, x) => {
                const isHighlighted = availableMoves.some((move) => move.x === x && move.y === y) && isMyTurn;
                return (
                  <div
                    key={`${x}-${y}`}
                    className={`cell${isHighlighted ? ' highlight' : ''}`}
                    onClick={() => handleCellClick(x, y)}
                    role="gridcell"
                  >
                    {cellValue === 1 || cellValue === 2 ? (
                      <div className={`disk ${cellValue === 1 ? 'black' : 'white'}`} />
                    ) : null}
                  </div>
                );
              })
            )}
          </div>
        </section>
      )}
    </main>
  );
}
