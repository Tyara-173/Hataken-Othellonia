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

    return flippable# othello_logic.py

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