'use client';

import { useEffect, useRef, useState } from 'react';
import { v4 as uuidv4 } from 'uuid';

const BOARD_SIZE = 6;
const BACKEND_BASE_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'https://hataken-othellonia-beta-qrhzeh4tlq-an.a.run.app';
const WS_BASE_URL = process.env.NEXT_PUBLIC_WS_URL || 'wss://hataken-othellonia-beta-qrhzeh4tlq-an.a.run.app';

function createInitialBoard() {
  return Array(BOARD_SIZE).fill(0).map(() => Array(BOARD_SIZE).fill(0));
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
  const [category, setCategory] = useState('');
  const [availableCategories, setAvailableCategories] = useState([]);
  const [message, setMessage] = useState('');
  const [playerNames, setPlayerNames] = useState({ 1: '-', 2: '-' });
  const [myColor, setMyColor] = useState(null);
  const [roomId, setRoomId] = useState(null);
  const [playerId, setPlayerId] = useState(null);
  const [board, setBoard] = useState(createInitialBoard());
  const [currentTurn, setCurrentTurn] = useState(1);
  const [availableMoves, setAvailableMoves] = useState([]);
  const [question, setQuestion] = useState(null);
  const [statusText, setStatusText] = useState('現在のターン: -');
  const [connectionError, setConnectionError] = useState('');
  const [surrenderProgress, setSurrenderProgress] = useState(0);
  const [gameOver, setGameOver] = useState(false);
  const [isRoomCreator, setIsRoomCreator] = useState(false);

  const wsRef = useRef(null);
  const surrenderTimerRef = useRef(null);

  // プレイヤーIDをlocalStorageで管理
  useEffect(() => {
    let storedPlayerId = localStorage.getItem('playerId');
    if (!storedPlayerId) {
      storedPlayerId = uuidv4();
      localStorage.setItem('playerId', storedPlayerId);
    }
    setPlayerId(storedPlayerId);

    const storedUsername = localStorage.getItem('username') || '';
    setUsername(storedUsername);
  }, []);

  // URLからroomIdを取得し、対戦に参加
  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    const urlRoomId = urlParams.get('roomId');
    if (urlRoomId) {
      setRoomId(urlRoomId);
      setScreen('category'); // ジャンル選択画面へ
    }
  }, []);

  // カテゴリリストを取得
  useEffect(() => {
    fetch(`${BACKEND_BASE_URL}/categories`)
      .then((res) => res.ok ? res.json() : { categories: [] })
      .then((data) => {
        const cats = data?.categories || [];
        setAvailableCategories(cats);
        if (cats.length > 0) {
          setCategory(cats[0]);
        }
      })
      .catch(() => setConnectionError("カテゴリの読み込みに失敗しました。"));
  }, []);

  const handleUsernameChange = (e) => {
    const newUsername = e.target.value;
    setUsername(newUsername);
    localStorage.setItem('username', newUsername);
  };

  const createRoom = () => {
    const newRoomId = uuidv4();
    setIsRoomCreator(true);
    setRoomId(newRoomId);
    // URLを更新してリロードせずにroomIdを反映
    window.history.pushState({}, '', `?roomId=${newRoomId}`);
    setScreen('category');
  };

  const copyInviteLink = () => {
    const url = window.location.href;
    navigator.clipboard.writeText(url)
      .then(() => setMessage("招待リンクをコピーしました！"))
      .catch(() => setMessage("コピーに失敗しました。"));
  };

  const resetGame = () => {
    setBoard(createInitialBoard());
    setCurrentTurn(1);
    setAvailableMoves([]);
    setQuestion(null);
    setGameOver(false);
    setMessage('');
    setStatusText('現在のターン: -');
    setMyColor(null);
    setPlayerNames({ 1: '-', 2: '-' });
  };

  const connectToRoom = () => {
    if (!roomId || !playerId) return;

    resetGame();
    setScreen('waiting');
    setMessage('接続中...');

    const ws = new WebSocket(`${WS_BASE_URL}/ws/${roomId}`);
    wsRef.current = ws;

    ws.onopen = () => {
      ws.send(JSON.stringify({
        action: 'join_room',
        player_id: playerId,
        username: username.trim() || '名無し',
        category: category, // ホストが選択したカテゴリ
      }));
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      switch (data.type) {
        case 'waiting':
          setScreen('waiting');
          setMessage(data.message);
          break;
        case 'start':
          setScreen('game');
          setMyColor(data.color);
          setBoard(data.board);
          setCurrentTurn(data.turn);
          setAvailableMoves(data.available_moves);
          setPlayerNames(data.player_names);
          setStatusText(`現在のターン: ${getTurnLabel(data.turn)}`);
          setMessage('ゲーム開始！');
          break;
        case 'update':
          setBoard(data.board);
          setCurrentTurn(data.turn);
          setAvailableMoves(data.available_moves);
          setQuestion(null);
          setStatusText(`現在のターン: ${getTurnLabel(data.turn)}`);
          if (data.message) setMessage(data.message);
          if (data.game_over) {
            setGameOver(true);
          }
          break;
        case 'question_prompt':
          setQuestion(data);
          setMessage('');
          break;
        case 'invalid_move':
        case 'error':
          setMessage(data.message);
          break;
        case 'opponent_disconnected':
          setGameOver(true);
          setMessage(data.message);
          if (wsRef.current) {
            wsRef.current.close();
            wsRef.current = null;
          }
          break;
      }
    };

    ws.onerror = () => {
      setConnectionError('WebSocket接続エラーが発生しました。');
      setScreen('title');
    };

    ws.onclose = () => {
      // 意図しない切断の場合のみメッセージを表示
      if (!gameOver) {
        setMessage('接続が切れました。');
      }
    };
  };

  const handleCellClick = (x, y) => {
    if (!wsRef.current || currentTurn !== myColor || gameOver) return;

    const isValidMove = availableMoves.some(move => move.x === x && move.y === y);
    if (!isValidMove) {
      setMessage("そこには置けません。");
      return;
    }

    wsRef.current.send(JSON.stringify({
      action: 'click_cell',
      player_id: playerId,
      color: myColor,
      x,
      y,
    }));
  };

  const handleAnswer = (choice) => {
    if (!wsRef.current || !question) return;
    wsRef.current.send(JSON.stringify({
      action: 'answer_question',
      player_id: playerId,
      selected_index: choice.index,
    }));
  };

  const handleSurrender = () => {
    if (!wsRef.current || gameOver) return;
    wsRef.current.send(JSON.stringify({
      action: 'surrender',
      player_id: playerId,
    }));
  };
  
  const handleSurrenderPressStart = () => {
    if (gameOver) return;
    surrenderTimerRef.current = setTimeout(() => {
      setSurrenderProgress(100);
      handleSurrender();
    }, 1000); // 1秒長押しで発動
  };

  const stopSurrenderHold = () => {
    clearTimeout(surrenderTimerRef.current);
    setSurrenderProgress(0);
  };

  const returnToTitle = () => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    window.history.pushState({}, '', window.location.pathname);
    setRoomId(null);
    setIsRoomCreator(false);
    resetGame();
    setScreen('title');
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
                onChange={handleUsernameChange}
                placeholder="名前を入力"
              />
            </div>
            {connectionError && <div className="error-text">{connectionError}</div>}
            <button className="match-btn" onClick={createRoom}>
              部屋を作成して対戦
            </button>
            <p style={{ marginTop: '1rem', fontSize: '0.9rem' }}>または、招待URLから参加してください。</p>
          </div>
        </section>
      )}

      {screen === 'category' && (
        <section className="screen">
          <div className="title-box">
            <h2>クイズジャンルを選択</h2>
            <div className="input-group">
              <label htmlFor="category">ジャンル</label>
              <select id="category" value={category} onChange={(e) => setCategory(e.target.value)} disabled={!isRoomCreator && roomId}>
                {availableCategories.length === 0 ? (
                  <option>読み込み中...</option>
                ) : (
                  availableCategories.map((name) => <option key={name} value={name}>{name}</option>)
                )}
              </select>
              {(!isRoomCreator && roomId) && <p style={{fontSize: '0.8rem'}}>ジャンルは部屋のホストが選択します。</p>}
            </div>
            <button className="match-btn" onClick={connectToRoom}>
              対戦を開始
            </button>
          </div>
        </section>
      )}

      {screen === 'waiting' && (
        <section className="screen">
          <div className="title-box">
            <h2>対戦相手を探しています...</h2>
            <p>{message}</p>
            <button className="match-btn" onClick={copyInviteLink} style={{marginTop: '1rem'}}>
              招待リンクをコピー
            </button>
          </div>
        </section>
      )}

      {screen === 'game' && (
        <section className="screen">
          <div className="info-panel">
            <div>先手: {playerNames[1]} / 後手: {playerNames[2]}</div>
            <div style={{ marginTop: 6 }}>あなたは: {myColor ? getColorLabel(myColor) : '-'}</div>
            <div className="status-text" style={{ color: isMyTurn ? '#dc2626' : '#1f2937' }}>
              {statusText}{isMyTurn ? ' (あなたの番です！)' : ''}
            </div>
            <div className="message-text">{message}</div>
            {gameOver && (
              <button className="match-btn" onClick={returnToTitle} style={{ marginTop: 12 }}>
                タイトルへ戻る
              </button>
            )}
          </div>

          {question && (
            <div className="question-panel">
              <div className="difficulty-tag">難易度: {question.difficulty}</div>
              <div className="question-text">{question.question}</div>
              <div className="choices-container">
                {question.choices.map((choice) => (
                  <button key={choice.index} className="choice-btn" onClick={() => handleAnswer(choice)}>
                    {choice.label}
                  </button>
                ))}
              </div>
            </div>
          )}

          <div className="board" role="grid">
            {board.map((row, y) =>
              row.map((cell, x) => {
                const isHighlight = availableMoves.some(m => m.x === x && m.y === y) && isMyTurn;
                return (
                  <div
                    key={`${x}-${y}`}
                    className={`cell${isHighlight ? ' highlight' : ''}`}
                    onClick={() => handleCellClick(x, y)}
                  >
                    {cell !== 0 && <div className={`disk ${cell === 1 ? 'black' : 'white'}`} />}
                  </div>
                );
              })
            )}
          </div>

          {!gameOver && (
            <button
              className="surrender-btn"
              onMouseDown={handleSurrenderPressStart}
              onMouseUp={stopSurrenderHold}
              onMouseLeave={stopSurrenderHold}
              onTouchStart={handleSurrenderPressStart}
              onTouchEnd={stopSurrenderHold}
            >
              長押しで降参
            </button>
          )}
        </section>
      )}
    </main>
  );
}
