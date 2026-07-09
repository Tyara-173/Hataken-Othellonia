# othello_logic.py

def get_flippable_disks(board, x, y, player):
    """
    石を置いた時に、ひっくり返せる石の座標リストを返す関数
    board: 6x6の2次元配列 (0:空, 1:黒, 2:白)
    x, y: 置きたい座標
    player: 1(黒) または 2(白)
    """
    if board[y][x] != 0:
        return [] # すでに石が置かれているマスには置けない

    opponent = 2 if player == 1 else 1
    # 8方向 (左上, 上, 右上, 左, 右, 左下, 下, 右下)
    directions = [(-1, -1), (0, -1), (1, -1), (-1, 0), (1, 0), (-1, 1), (0, 1), (1, 1)]
    
    flippable = []

    for dx, dy in directions:
        nx, ny = x + dx, y + dy
        temp_flippable = []

        # 盤面内で、かつ相手の石である限り進み続ける
        while 0 <= nx < 6 and 0 <= ny < 6 and board[ny][nx] == opponent:
            temp_flippable.append((nx, ny))
            nx += dx
            ny += dy

        # 相手の石を飛び越えた先が「自分の石」なら、ひっくり返せる
        if temp_flippable and 0 <= nx < 6 and 0 <= ny < 6 and board[ny][nx] == player:
            flippable.extend(temp_flippable)

    return flippable


def has_valid_moves(board, player, excluded_positions=None):
    """
    指定したプレイヤーが盤面のどこかに石を置けるか判定する
    excluded_positions: そのターンに既に選択した座標の集合
    """
    if excluded_positions is None:
        excluded_positions = set()
    else:
        excluded_positions = set(excluded_positions)

    for y in range(6):
        for x in range(6):
            if board[y][x] == 0 and (x, y) not in excluded_positions:
                if len(get_flippable_disks(board, x, y, player)) > 0:
                    return True
    return False

def get_score(board):
    """
    黒(1)と白(2)の石の数を数える
    """
    black = 0
    white = 0
    for row in board:
        for cell in row:
            if cell == 1:
                black += 1
            elif cell == 2:
                white += 1
    return {"black": black, "white": white}