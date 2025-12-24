from typing import List, Optional, Literal

from fastapi import Depends, FastAPI, HTTPException, Path, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlmodel import Session

from src.db.database import init_db, get_session
from src.db.repositories import PlayerRepository, GameRepository, MoveRepository, LeaderboardService
from src.db.models import GameStatus
from src.api.game_service import (
    create_new_game,
    apply_move,
    board_to_list,
    compute_current_player,
    map_status_for_api,
    map_winner_for_api,
)

openapi_tags = [
    {"name": "health", "description": "Service health checks"},
    {"name": "players", "description": "Player management"},
    {"name": "games", "description": "Game lifecycle and state"},
    {"name": "leaderboard", "description": "Leaderboard and statistics"},
    {"name": "internal", "description": "Internal utilities and bootstrapping"},
]

app = FastAPI(
    title="Tic Tac Toe Backend",
    description="Backend service for Tic Tac Toe: players, games, moves, history, and leaderboard.",
    version="0.1.0",
    openapi_tags=openapi_tags,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Can be restricted via env later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    """Initialize database and create tables on service startup."""
    init_db(echo=False)


# PUBLIC_INTERFACE
@app.get("/", tags=["health"], summary="Health Check", description="Basic health check endpoint.")
def health_check():
    """Return a simple service health response."""
    return {"message": "Healthy"}


# ---- Schemas for API I/O ----

class PlayerCreate(BaseModel):
    username: str = Field(..., min_length=1, max_length=50, description="Unique username")
    display_name: Optional[str] = Field(None, max_length=100, description="Optional display name")


class PlayerOut(BaseModel):
    id: int
    username: str
    display_name: Optional[str]


class CreateGameRequest(BaseModel):
    player_x_id: Optional[int] = Field(None, description="Player ID for X")
    player_o_id: Optional[int] = Field(None, description="Player ID for O")


class GameState(BaseModel):
    id: int
    board: List[str] = Field(..., min_items=9, max_items=9, description="Board as 9 strings")
    currentPlayer: Literal["X", "O"]
    status: Literal["in-progress", "won", "draw"]
    winner: Optional[Literal["X", "O"]] = None


class MoveRequest(BaseModel):
    position: int = Field(..., ge=0, le=8, description="Cell index 0..8")
    player_id: Optional[int] = Field(None, description="Optional actor player id for validation")


class MoveHistoryItem(BaseModel):
    id: int
    position: int
    player: Literal["X", "O"]


class LeaderboardEntry(BaseModel):
    username: str
    wins: int
    losses: int
    draws: int
    score: int


# ---- Routes ----

# PUBLIC_INTERFACE
@app.post(
    "/players",
    tags=["players"],
    summary="Create player",
    description="Create and persist a new player with unique username.",
    response_model=PlayerOut,
    responses={
        400: {"description": "Username already exists"},
    },
)
def create_player(payload: PlayerCreate, session: Session = Depends(get_session)) -> PlayerOut:
    """Create a player if username is unique."""
    repo = PlayerRepository(session)
    existing = repo.get_by_username(payload.username)
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")
    player = repo.create(username=payload.username, display_name=payload.display_name)
    return PlayerOut(id=player.id, username=player.username, display_name=player.display_name)


# PUBLIC_INTERFACE
@app.post(
    "/games",
    tags=["games"],
    summary="Create game",
    description="Create a new game with optional players. Board starts empty, X's turn.",
    response_model=GameState,
)
def create_game(payload: CreateGameRequest = Body(default=CreateGameRequest()), session: Session = Depends(get_session)) -> GameState:
    """Create a new game and return its initial state."""
    game = create_new_game(session, player_x_id=payload.player_x_id, player_o_id=payload.player_o_id)
    state = GameState(
        id=game.id,
        board=board_to_list(game.board),
        currentPlayer=compute_current_player(game.board),
        status=map_status_for_api(game.status),
        winner=None,
    )
    return state


# PUBLIC_INTERFACE
@app.get(
    "/games/{game_id}",
    tags=["games"],
    summary="Get game",
    description="Fetch current game state with board, current player, status, and winner if any.",
    response_model=GameState,
    responses={404: {"description": "Game not found"}},
)
def get_game(
    game_id: int = Path(..., description="Game ID"),
    session: Session = Depends(get_session),
) -> GameState:
    """Return game state for a game id."""
    gr = GameRepository(session)
    game = gr.get_by_id(game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    state = GameState(
        id=game.id,
        board=board_to_list(game.board),
        currentPlayer=compute_current_player(game.board) if game.status == GameStatus.IN_PROGRESS else ("X" if game.status == GameStatus.O_WON else "O") if game.status in (GameStatus.X_WON, GameStatus.O_WON) else "X",
        status=map_status_for_api(game.status),
        winner=map_winner_for_api(game.status),
    )
    return state


# PUBLIC_INTERFACE
@app.post(
    "/games/{game_id}/moves",
    tags=["games"],
    summary="Make move",
    description="Apply a move at a board position for the current player.",
    response_model=GameState,
    responses={
        400: {"description": "Invalid move"},
        404: {"description": "Game not found"},
    },
)
def make_move(
    game_id: int = Path(..., description="Game ID"),
    payload: MoveRequest = Body(...),
    session: Session = Depends(get_session),
) -> GameState:
    """Validate and apply a move; return updated game state."""
    game, err = apply_move(session, game_id=game_id, position=payload.position, player_id=payload.player_id)
    if game is None:
        if err == "Game not found":
            raise HTTPException(status_code=404, detail=err)
        raise HTTPException(status_code=400, detail=err)

    state = GameState(
        id=game.id,
        board=board_to_list(game.board),
        currentPlayer=compute_current_player(game.board) if game.status == GameStatus.IN_PROGRESS else ("X" if game.status == GameStatus.O_WON else "O") if game.status in (GameStatus.X_WON, GameStatus.O_WON) else "X",
        status=map_status_for_api(game.status),
        winner=map_winner_for_api(game.status),
    )
    return state


# PUBLIC_INTERFACE
@app.get(
    "/games/{game_id}/history",
    tags=["games"],
    summary="Game history",
    description="Return chronological move history for a game.",
    response_model=List[MoveHistoryItem],
    responses={404: {"description": "Game not found"}},
)
def game_history(
    game_id: int = Path(..., description="Game ID"),
    session: Session = Depends(get_session),
) -> List[MoveHistoryItem]:
    """Return moves as array of { id, position, player }."""
    gr = GameRepository(session)
    mr = MoveRepository(session)
    game = gr.get_by_id(game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    moves = mr.list_for_game(game_id)
    items: List[MoveHistoryItem] = []
    for m in moves:
        items.append(MoveHistoryItem(id=m.id, position=m.position, player=m.mark))  # mark is X/O
    return items


# PUBLIC_INTERFACE
@app.get(
    "/leaderboard",
    tags=["leaderboard"],
    summary="Leaderboard",
    description="Return player stats with wins, losses, draws, and score.",
    response_model=List[LeaderboardEntry],
)
def leaderboard(session: Session = Depends(get_session)) -> List[LeaderboardEntry]:
    """Compute simple leaderboard from stored games."""
    # Compute wins first
    ls = LeaderboardService(session)
    win_list = ls.compute(limit=1000)  # username->wins
    wins_map = {u: w for u, w in win_list}

    # Compute losses and draws by scanning games
    gr = GameRepository(session)
    # Pull all games for a simple pass (small dataset expected)
    games = gr.list(limit=10000, offset=0)
    losses_map: dict[str, int] = {}
    draws_map: dict[str, int] = {}

    # Map player ids to usernames for faster lookup
    from src.db.repositories import PlayerRepository as PR
    pr = PR(session)
    cache: dict[int, str] = {}

    def username_for(player_id: Optional[int]) -> Optional[str]:
        if not player_id:
            return None
        if player_id in cache:
            return cache[player_id]
        p = pr.get_by_id(player_id)
        if not p:
            return None
        cache[player_id] = p.username
        return cache[player_id]

    for g in games:
        if g.status == GameStatus.DRAW:
            ux = username_for(g.player_x_id)
            uo = username_for(g.player_o_id)
            if ux:
                draws_map[ux] = draws_map.get(ux, 0) + 1
            if uo:
                draws_map[uo] = draws_map.get(uo, 0) + 1
        elif g.status in (GameStatus.X_WON, GameStatus.O_WON):
            ux = username_for(g.player_x_id)
            uo = username_for(g.player_o_id)
            if g.status == GameStatus.X_WON:
                # O loses
                if uo:
                    losses_map[uo] = losses_map.get(uo, 0) + 1
            elif g.status == GameStatus.O_WON:
                # X loses
                if ux:
                    losses_map[ux] = losses_map.get(ux, 0) + 1

    # Combine into entries; include players who only have losses/draws
    usernames = set(wins_map.keys()) | set(losses_map.keys()) | set(draws_map.keys())
    entries: List[LeaderboardEntry] = []
    for u in sorted(usernames):
        w = wins_map.get(u, 0)
        l = losses_map.get(u, 0)
        d = draws_map.get(u, 0)
        # Simple score: win=3, draw=1, loss=0
        score = w * 3 + d * 1
        entries.append(LeaderboardEntry(username=u, wins=w, losses=l, draws=d, score=score))

    return entries
