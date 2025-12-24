from __future__ import annotations

from typing import List, Optional, Tuple

from sqlmodel import Session, select

from src.db.models import Game, Move, Player, GameStatus


# PUBLIC_INTERFACE
class PlayerRepository:
    """CRUD operations for Player."""

    def __init__(self, session: Session):
        self.session = session

    # PUBLIC_INTERFACE
    def create(self, username: str, display_name: Optional[str] = None) -> Player:
        """Create and persist a player."""
        player = Player(username=username, display_name=display_name)
        self.session.add(player)
        self.session.flush()  # assign ID
        return player

    # PUBLIC_INTERFACE
    def get_by_id(self, player_id: int) -> Optional[Player]:
        """Fetch player by id."""
        return self.session.get(Player, player_id)

    # PUBLIC_INTERFACE
    def get_by_username(self, username: str) -> Optional[Player]:
        """Fetch player by unique username."""
        stmt = select(Player).where(Player.username == username)
        return self.session.exec(stmt).first()

    # PUBLIC_INTERFACE
    def list(self, limit: int = 100, offset: int = 0) -> List[Player]:
        """List players with pagination."""
        stmt = select(Player).offset(offset).limit(limit)
        return list(self.session.exec(stmt))

    # PUBLIC_INTERFACE
    def delete(self, player_id: int) -> bool:
        """Delete a player by id."""
        player = self.get_by_id(player_id)
        if not player:
            return False
        self.session.delete(player)
        return True


# PUBLIC_INTERFACE
class GameRepository:
    """CRUD operations for Game."""

    def __init__(self, session: Session):
        self.session = session

    # PUBLIC_INTERFACE
    def create(self, player_x_id: Optional[int] = None, player_o_id: Optional[int] = None) -> Game:
        """Create a new game with optional participants."""
        game = Game(player_x_id=player_x_id, player_o_id=player_o_id)
        self.session.add(game)
        self.session.flush()
        return game

    # PUBLIC_INTERFACE
    def get_by_id(self, game_id: int) -> Optional[Game]:
        """Fetch game by id."""
        return self.session.get(Game, game_id)

    # PUBLIC_INTERFACE
    def update_board_and_status(
        self, game_id: int, board: str, status: GameStatus, winner: Optional[str] = None
    ) -> Optional[Game]:
        """Update game board and status."""
        game = self.get_by_id(game_id)
        if not game:
            return None
        game.board = board
        game.status = status
        game.winner = winner
        if status in (GameStatus.X_WON, GameStatus.O_WON, GameStatus.DRAW):
            from datetime import datetime
            game.finished_at = datetime.utcnow()
        return game

    # PUBLIC_INTERFACE
    def list(self, limit: int = 100, offset: int = 0) -> List[Game]:
        """List games with pagination."""
        stmt = select(Game).order_by(Game.id.desc()).offset(offset).limit(limit)
        return list(self.session.exec(stmt))


# PUBLIC_INTERFACE
class MoveRepository:
    """CRUD operations for Move."""

    def __init__(self, session: Session):
        self.session = session

    # PUBLIC_INTERFACE
    def create(self, game_id: int, position: int, mark: str, player_id: Optional[int] = None) -> Move:
        """Create and persist a move."""
        move = Move(game_id=game_id, position=position, mark=mark, player_id=player_id)
        self.session.add(move)
        self.session.flush()
        return move

    # PUBLIC_INTERFACE
    def list_for_game(self, game_id: int) -> List[Move]:
        """List moves for a game in ID (insertion) order."""
        stmt = select(Move).where(Move.game_id == game_id).order_by(Move.id.asc())
        return list(self.session.exec(stmt))


# PUBLIC_INTERFACE
class LeaderboardService:
    """Basic leaderboard computation based on stored games."""

    def __init__(self, session: Session):
        self.session = session

    # PUBLIC_INTERFACE
    def compute(self, limit: int = 10) -> List[Tuple[str, int]]:
        """Return top players by win count."""
        # naive approach: scan games and count wins
        wins: dict[str, int] = {}
        games = select(Game)
        for g in self.session.exec(games):
            if g.status in (GameStatus.X_WON, GameStatus.O_WON):
                winner_username: Optional[str] = None
                if g.status == GameStatus.X_WON and g.player_x_id:
                    p = self.session.get(Player, g.player_x_id)
                    winner_username = p.username if p else None
                elif g.status == GameStatus.O_WON and g.player_o_id:
                    p = self.session.get(Player, g.player_o_id)
                    winner_username = p.username if p else None
                if winner_username:
                    wins[winner_username] = wins.get(winner_username, 0) + 1
        # sort and cap
        sorted_items = sorted(wins.items(), key=lambda x: x[1], reverse=True)
        return sorted_items[:limit]
