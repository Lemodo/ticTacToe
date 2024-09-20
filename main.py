from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uuid

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # alle Ursprünge
    allow_credentials=True,
    allow_methods=["*"],  # alle Methoden
    allow_headers=["*"],  # alle Header
)

class Move(BaseModel):
    player: str
    row: int
    col: int

class Game(BaseModel):
    id: str
    board: list
    current_player: str
    against_algorithm: bool

games = {}

def check_winner(board: list[list[str]]) -> str | None:
    """
    Überprüft, ob es einen Gewinner auf dem Spielbrett gibt.
    :param board: Das aktuelle Spielbrett
    :return: Der Gewinner ('X' oder 'O') oder None, wenn es keinen Gewinner gibt
    """
    for i in range(3):
        if board[i][0] == board[i][1] == board[i][2] != "":
            return board[i][0]
        if board[0][i] == board[1][i] == board[2][i] != "":
            return board[0][i]
    if board[0][0] == board[1][1] == board[2][2] != "":
        return board[0][0]
    if board[0][2] == board[1][1] == board[2][0] != "":
        return board[0][2]
    return None

def check_tie(board: list[list[str]]) -> bool:
    # Überprüfen, ob das Spielfeld voll ist und kein Gewinner vorhanden ist
    for row in board:
        if "" in row:
            return False
    return True

def make_algorithm_move(board: list[list[str]]) -> None:
    """
    Führt einen Zug für den Algorithmus (Spieler 'O') aus.
    :param board: Das aktuelle Spielbrett
    """
    best_score = float('-inf')
    best_move = None

    for i in range(3):
        for j in range(3):
            if board[i][j] == "":
                board[i][j] = "O"
                score = minimax(board, 0, False)
                board[i][j] = ""
                if score > best_score:
                    best_score = score
                    best_move = (i, j)

    if best_move:
        board[best_move[0]][best_move[1]] = "O"

def minimax(board: list[list[str]], depth: int, is_maximizing: bool) -> int:
    """
    Implementiert den Minimax-Algorithmus, um den optimalen Zug zu finden.
    https://en.wikipedia.org/wiki/Minimax

    :param board: Das aktuelle Spielbrett
    :param depth: Die aktuelle Tiefe des Minimax-Baums
    :param is_maximizing: Ob der aktuelle Spieler maximiert
    :return: Der beste Score für den aktuellen Spieler
    """
    winner = check_winner(board)
    if winner == "O":
        return 1
    elif winner == "X":
        return -1
    elif all(cell != "" for row in board for cell in row):
        return 0

    if is_maximizing:
        best_score = float('-inf')
        for i in range(3):
            for j in range(3):
                if board[i][j] == "":
                    board[i][j] = "O"
                    score = minimax(board, depth + 1, False)
                    board[i][j] = ""
                    best_score = max(score, best_score)
        return best_score
    else:
        best_score = float('inf')
        for i in range(3):
            for j in range(3):
                if board[i][j] == "":
                    board[i][j] = "X"
                    score = minimax(board, depth + 1, True)
                    board[i][j] = ""
                    best_score = min(score, best_score)
        return best_score

@app.post("/create_game")
async def create_game(against_algorithm: bool) -> dict[str, str]:
    """
    Erstellt ein neues Spiel.
    :param against_algorithm: Ob gegen den Algorithmus gespielt wird
    :return: Die ID des erstellten Spiels
    """
    game_id = str(uuid.uuid4())
    games[game_id] = Game(
        id=game_id,
        board=[["" for _ in range(3)] for _ in range(3)],
        current_player="X",
        against_algorithm=against_algorithm
    )
    return {"game_id": game_id}

@app.get("/board/{game_id}")
async def get_board(game_id: str) -> dict[str, list[list[str]]]:
    """
    Gibt das aktuelle Spielbrett zurück.
    :param game_id: Die ID des Spiels
    :return: Das aktuelle Spielbrett
    """
    if game_id not in games:
        raise HTTPException(status_code=404, detail="Game not found")
    return {"board": games[game_id].board}

@app.post("/move/{game_id}")
async def make_move(game_id: str, move: Move) -> dict[str, str | list[list[str]]]:
    """
    Führt einen Zug im Spiel aus.
    :param game_id: Die ID des Spiels
    :param move: Der Zug, der ausgeführt werden soll
    :return: Das aktualisierte Spielbrett und der nächste Spieler oder eine Gewinnmeldung
    """
    if game_id not in games:
        raise HTTPException(status_code=404, detail="Game not found")

    game = games[game_id]
    if game.board[move.row][move.col] != "":
        raise HTTPException(status_code=400, detail="Cell already taken")
    if move.player != game.current_player:
        raise HTTPException(status_code=400, detail="Not your turn")

    game.board[move.row][move.col] = move.player
    winner = check_winner(game.board)
    if winner:
        return {"message": f"Player {winner} wins!", "board": game.board}

    if check_tie(game.board):
        return {"message": "It's a tie!", "board": game.board}

    game.current_player = "O" if game.current_player == "X" else "X"

    if game.against_algorithm and game.current_player == "O":
        make_algorithm_move(game.board)
        winner = check_winner(game.board)
        if winner:
            return {"message": f"Player {winner} wins!", "board": game.board}
        if check_tie(game.board):
            return {"message": "It's a tie!", "board": game.board}
        game.current_player = "X"

    return {"board": game.board, "next_player": game.current_player}