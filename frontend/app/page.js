'use client';

import { useEffect, useRef, useState } from 'react';

const BOARD_SIZE = 6;
const BACKEND_BASE_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'https://hataken-othellonia-beta-qrhzeh4tlq-an.a.run.app';
const WS_BASE_URL = process.env.NEXT_PUBLIC_WS_URL || 'wss://hataken-othellonia-beta-qrhzeh4tlq-an.a.run.app';

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
  const [availableBgm, setAvailableBgm] = useState({ title: false, game: false, end: false });
  const [availableSe, setAvailableSe] = useState({ click: false, no_stone: false, quiz: false, correct: false, incorrect: false });

  const wsRef = useRef(null);
  const roomRef = useRef(null);
  const playerRef = useRef(null);
  const colorRef = useRef(null);
  const audioRef = useRef(null);
  const seAudioRef = useRef(null);
  const surrenderTimerRef = useRef(null);
  const surrenderStartRef = useRef(null);

  useEffect(() => {
    fetch(`${BACKEND_BASE_URL}/categories`)
      .then((response) => response.ok ? response.json() : { categories: [] })
      .then((data) => {
        const categories = data?.categories || [];
        setAvailableCategories(categories);
        setCategory((currentCategory) => {
          if (categories.includes(currentCategory)) {
            return currentCategory;
          }
          return categories[0] || '';
        });
      })
      .catch(() => {
        setAvailableCategories([]);
        setCategory('');
      });

    const checkTrack = async (name) => {
      try {
        const response = await fetch(`/bgm/${name}.mp3`, { method: 'HEAD' });
        return response.ok;
      } catch {
        return false;
      }
    };

    const loadAvailableBgm = async () => {
      const [title, game, end] = await Promise.all([
        checkTrack('title'),
        checkTrack('game'),
        checkTrack('end'),
      ]);
      setAvailableBgm({ title, game, end });
    };

    const checkSeTrack = async (name) => {
      try {
        const response = await fetch(`/se/${name}.mp3`, { method: 'HEAD' });
        return response.ok;
      } catch {
        return false;
      }
    };

    const loadAvailableSe = async () => {
      const [click, no_stone, quiz, correct, incorrect] = await Promise.all([
        checkSeTrack('click'),
        checkSeTrack('no_stone'),
        checkSeTrack('quiz'),
        checkSeTrack('correct'),
        checkSeTrack('incorrect'),
      ]);
      setAvailableSe({ click, no_stone, quiz, correct, incorrect });
    };

    loadAvailableBgm();
    loadAvailableSe();

    return () => {
      if (surrenderTimerRef.current) {
        window.clearTimeout(surrenderTimerRef.current);
      }
      if (wsRef.current && wsRef.current.readyState === 1) {
        wsRef.current.close();
      }
      audioRef.current?.pause();
    };
  }, []);

  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) {
      return;
    }

    const activeTrack = screen === 'title'
      ? (availableBgm.title ? 'title' : null)
      : gameOver
        ? (availableBgm.end ? 'end' : null)
        : screen === 'game'
          ? (availableBgm.game ? 'game' : null)
          : null;

    if (!activeTrack) {
      audio.pause();
      audio.currentTime = 0;
      return;
    }

    audio.loop = true;
    audio.volume = 0.35;
    audio.src = `/bgm/${activeTrack}.mp3`;
    audio.load();
    audio.play().catch(() => {});
  }, [availableBgm, gameOver, screen]);

  const playSe = (type) => {
    const audio = seAudioRef.current;
    if (!audio || !availableSe[type]) {
      return;
    }
    console.log(`Playing SE: ${type}`);
    audio.currentTime = 0;
    audio.volume = 0.5;
    audio.src = `/se/${type}.mp3`;
    audio.load();
    audio.play().catch(() => {});
  };

  const resetToTitle = (message = '') => {
    setScreen('title');
    setConnectionError(message);
    setMessage('');
    setQuestion(null);
    setBoard(createInitialBoard());
    setCurrentTurn(1);
    setAvailableMoves([]);
    setStatusText('現在のターン: -');
    setRoomId(null);
    setPlayerId(null);
    roomRef.current = null;
    playerRef.current = null;
    setMyColor(null);
    colorRef.current = null;
    setPlayerNames({ 1: '-', 2: '-' });
    setSurrenderProgress(0);
    setGameOver(false);
  };

  const returnToTitleWithConfirm = (message) => {
    const shouldReturn = window.confirm(`${message}\nOKを押すとタイトルに戻ります。`);
    if (!shouldReturn) {
      return;
    }

    resetToTitle(message);
  };

  const handleReturnToTitle = () => {
    const ws = wsRef.current;
    wsRef.current = null;
    if (ws && ws.readyState === 1) {
      ws.close();
    }
    resetToTitle('');
  };

  const startMatch = () => {
    const ws = new WebSocket(`${WS_BASE_URL}/ws`);

    setScreen('waiting');
    setQuestion(null);
    setMessage('');
    setConnectionError('');
    setBoard(createInitialBoard());
    setCurrentTurn(1);
    setAvailableMoves([]);
    setStatusText('現在のターン: -');
    setSurrenderProgress(0);
    setGameOver(false);

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
        setPlayerId(data.player_id);
        roomRef.current = data.room_id;
        playerRef.current = data.player_id;
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
        playSe('quiz');
      } else if (data.type === 'update') {
        setBoard(data.board || createInitialBoard());
        setCurrentTurn(data.turn || 1);
        setAvailableMoves(data.available_moves || []);
        setQuestion(null);
        setStatusText(`現在のターン: ${getTurnLabel(data.turn || 1)}`);
        setGameOver(Boolean(data.game_over));
        if (data.message) {
          setMessage(data.message);
        }
      } else if (data.type === 'invalid_move') {
        setMessage(data.message || 'その手は無効です。');
      } else if (data.type === 'answer_result') {
        playSe(data.correct ? 'correct' : 'incorrect');
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
      playSe('click');
      return;
    }

    const cellValue = board[y]?.[x];
    const isValidPlacement = availableMoves.some((move) => move.x === x && move.y === y);
    const isOccupied = cellValue === 1 || cellValue === 2;

    if (!isValidPlacement || isOccupied) {
      playSe('no_stone');
      return;
    }

    wsRef.current.send(JSON.stringify({
      action: 'click_cell',
      room_id: roomRef.current,
      player_id: playerRef.current,
      color: colorRef.current,
      x,
      y,
    }));
  };

  const handleAnswer = (choice) => {
    if (!wsRef.current || !roomRef.current || !colorRef.current || !playerRef.current) {
      return;
    }

    playSe('quiz');
    wsRef.current.send(JSON.stringify({
      action: 'answer_question',
      room_id: roomRef.current,
      player_id: playerRef.current,
      color: colorRef.current,
      selected_index: choice.index,
    }));
  };

  const stopSurrenderHold = () => {
    if (surrenderTimerRef.current) {
      window.clearTimeout(surrenderTimerRef.current);
      surrenderTimerRef.current = null;
    }
    surrenderStartRef.current = null;
    setSurrenderProgress(0);
  };

  const handleSurrender = () => {
    if (!wsRef.current || !roomRef.current || !colorRef.current || !playerRef.current) {
      stopSurrenderHold();
      return;
    }

    stopSurrenderHold();
    wsRef.current.send(JSON.stringify({
      action: 'surrender',
      room_id: roomRef.current,
      player_id: playerRef.current,
      color: colorRef.current,
    }));
  };

  const handleSurrenderPressStart = () => {
    if (!wsRef.current || !roomRef.current || !colorRef.current || !playerRef.current) {
      return;
    }

    surrenderStartRef.current = Date.now();
    setSurrenderProgress(0);

    const tick = () => {
      const elapsed = Date.now() - surrenderStartRef.current;
      const progress = Math.min(100, Math.round((elapsed / 1000) * 100));
      setSurrenderProgress(progress);

      if (progress >= 100) {
        handleSurrender();
        return;
      }

      surrenderTimerRef.current = window.setTimeout(tick, 50);
    };

    if (surrenderTimerRef.current) {
      window.clearTimeout(surrenderTimerRef.current);
    }
    tick();
  };

  const isMyTurn = currentTurn === myColor;

  return (
    <main>
      <audio ref={audioRef} preload="auto" />
      <audio ref={seAudioRef} preload="auto" />
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
            <button className="match-btn" onClick={() => {
              playSe('click');
              setScreen('category');
            }}>
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
                {availableCategories.length === 0 ? (
                  <option value="">読み込み中...</option>
                ) : (
                  availableCategories.map((name) => (
                    <option key={name} value={name}>{name}</option>
                  ))
                )}
              </select>
            </div>
            <button className="match-btn" onClick={() => {
              playSe('click');
              startMatch();
            }}>
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
            {gameOver ? (
              <button className="match-btn" onClick={() => {
                playSe('click');
                handleReturnToTitle();
              }} style={{ marginTop: 12 }}>
                タイトルへ戻る
              </button>
            ) : null}
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

          {!gameOver ? (
            <button
              className="surrender-btn"
              type="button"
              onMouseDown={handleSurrenderPressStart}
              onMouseUp={stopSurrenderHold}
              onMouseLeave={stopSurrenderHold}
              onTouchStart={handleSurrenderPressStart}
              onTouchEnd={stopSurrenderHold}
              onTouchCancel={stopSurrenderHold}
              onClick={(event) => event.preventDefault()}
              style={{
                background: `linear-gradient(135deg, #fff7ed 0%, #f59e0b ${surrenderProgress}%, #fff7ed ${surrenderProgress}%, #fff7ed 100%)`,
              }}
            >
              {surrenderProgress > 0 ? `長押し中... ${surrenderProgress}%` : '長押しで降参'}
            </button>
          ) : null}
        </section>
      )}
    </main>
  );
}
