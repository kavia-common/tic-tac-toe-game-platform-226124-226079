from __future__ import annotations

from typing import List, Optional, Tuple

from sqlmodel import Session

from src.db.models import Game, GameStatus
from src.db.repositories import GameRepository, MoveRepository


# PUBLIC_INTERFACE
def board_to_list(board: str) -> List[str]:
    """Convert board string to list of 9 strings."""
    return list(board)


# PUBLIC_INTERFACE
def list_to_board(cells: List[str]) -> str:
    """Convert list of 9 strings to board string."""
    return "".join(cells)


# PUBLIC_INTERFACE
def compute_current_player(board: str) -> str:
    """Compute current player from board: X starts; if equal counts, X; else O."""
    x_count = board.count("X")
    o_count = board.count("O")
    return "X" if x_count == o_count else "O"


WIN_LINES: Tuple[Tuple[int, int, int], ...] = (
    (0, 1, 2),
    (3, 4, 5),
    (6, 7, 8),
    (0, 3, 6),
    (1, 4, 7),
    (2, 5, 8),
    (0, 4, 8),
    (2, 4, 6),
)


# PUBLIC_INTERFACE
def detect_winner(board: str) -> Optional[str]:
    """Return 'X' or 'O' if there's a winner, otherwise None."""
    cells = board_to_list(board)
    for a, b, c in WIN_LINES:
        if cells[a] != " " and cells[a] == cells[b] == cells[c]:
            return cells[a]
    return None


# PUBLIC_INTERFACE
def is_draw(board: str) -> bool:
    """True if board is full and no winner."""
    return " " not in board and detect_winner(board) is None


# PUBLIC_INTERFACE
def map_status_for_api(status: GameStatus) -> str:
    """Map internal GameStatus to API's 'status' field."""
    if status == GameStatus.IN_PROGRESS:
        return "in-progress"
    if status == GameStatus.DRAW:
        return "draw"
    if status in (GameStatus.X_WON, GameStatus.O_WON):
        return "won"
    # default
    return "in-progress"


# PUBLIC_INTERFACE
def map_winner_for_api(status: GameStatus) -> Optional[str]:
    """Return 'X'|'O' for winner if applicable."""
    if status == GameStatus.X_WON:
        return "X"
    if status == GameStatus.O_WON:
        return "O"
    return None


# PUBLIC_INTERFACE
def create_new_game(session: Session, player_x_id: Optional[int] = None, player_o_id: Optional[int] = None) -> Game:
    """Create a game with empty board and X to start."""
    gr = GameRepository(session)
    game = gr.create(player_x_id=player_x_id, player_o_id=player_o_id)
    # defaults in model already set: board to spaces, status in_progress
    return game


# PUBLIC_INTERFACE
def apply_move(session: Session, game_id: int, position: int, player_id: Optional[int] = None) -> Tuple[Optional[Game], Optional[str]]:
    """Validate and apply a move. Returns (game, error_message)."""
    gr = GameRepository(session)
    mr = MoveRepository(session)

    game = gr.get_by_id(game_id)
    if not game:
        return None, "Game not found"

    if game.status != GameStatus.IN_PROGRESS:
        return None, "Game is not in progress"

    if position < 0 or position > 8:
        return None, "Position must be between 0 and 8"

    board_cells = board_to_list(game.board)
    if board_cells[position] != " ":
        return None, "Cell already occupied"

    # Determine whose turn it is and expected mark
    current_player_mark = compute_current_player(game.board)

    # Optional enforcement when players are assigned
    if game.player_x_id or game.player_o_id:
        # if a player id is provided, ensure it matches turn
        if player_id is not None:
            if current_player_mark == "X" and game.player_x_id and player_id != game.player_x_id:
                return None, "It is X's turn"
            if current_player_mark == "O" and game.player_o_id and player_id != game.player_o_id:
                return None, "It is O's turn"

    # Apply move
    board_cells[position] = current_player_mark
    new_board = list_to_board(board_cells)

    # Persist move
    mr.create(game_id=game.id, position=position, mark=current_player_mark, player_id=player_id)

    # Determine status
    winner = detect_winner(new_board)
    if winner == "X":
        status = GameStatus.X_WON
    elif winner == "O":
        status = GameStatus.O_WON
    elif is_draw(new_board):
        status = GameStatus.DRAW
    else:
        status = GameStatus.IN_PROGRESS

    gr.update_board_and_status(game.id, new_board, status, winner=winner if winner else None)

    return game, None
