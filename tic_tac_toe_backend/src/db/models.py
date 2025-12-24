from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Optional

from sqlmodel import Field, Relationship, SQLModel


class GameStatus(str, Enum):
    IN_PROGRESS = "in_progress"
    X_WON = "x_won"
    O_WON = "o_won"
    DRAW = "draw"


class PlayerBase(SQLModel):
    username: str = Field(index=True, unique=True, min_length=1, max_length=50, description="Unique player username")
    display_name: Optional[str] = Field(default=None, max_length=100, description="Optional display name")


class Player(PlayerBase, table=True):
    """Player persisted model."""
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")

    games_as_x: List["Game"] = Relationship(back_populates="player_x", sa_relationship_kwargs={"foreign_keys": "[Game.player_x_id]"})
    games_as_o: List["Game"] = Relationship(back_populates="player_o", sa_relationship_kwargs={"foreign_keys": "[Game.player_o_id]"})

    moves: List["Move"] = Relationship(back_populates="player")


class GameBase(SQLModel):
    status: GameStatus = Field(default=GameStatus.IN_PROGRESS, description="Current game status")
    # board is a simple string of 9 chars: [XO ]*9 for current state
    board: str = Field(default=" " * 9, min_length=9, max_length=9, description="Linearized 3x3 board")
    winner: Optional[str] = Field(default=None, description="Winner mark 'X' or 'O' if finished")
    started_at: datetime = Field(default_factory=datetime.utcnow)
    finished_at: Optional[datetime] = None


class Game(GameBase, table=True):
    """Game persisted model."""
    id: Optional[int] = Field(default=None, primary_key=True)

    player_x_id: Optional[int] = Field(default=None, foreign_key="player.id")
    player_o_id: Optional[int] = Field(default=None, foreign_key="player.id")

    player_x: Optional[Player] = Relationship(back_populates="games_as_x", sa_relationship_kwargs={"foreign_keys": "[Game.player_x_id]"})
    player_o: Optional[Player] = Relationship(back_populates="games_as_o", sa_relationship_kwargs={"foreign_keys": "[Game.player_o_id]"})

    moves: List["Move"] = Relationship(back_populates="game")


class MoveBase(SQLModel):
    position: int = Field(ge=0, le=8, description="Board index 0..8")
    mark: str = Field(regex="^[XO]$", description="Mark placed: 'X' or 'O'")
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Move(MoveBase, table=True):
    """Move persisted model."""
    id: Optional[int] = Field(default=None, primary_key=True)
    game_id: int = Field(foreign_key="game.id", index=True)
    player_id: Optional[int] = Field(default=None, foreign_key="player.id", index=True)

    game: Game = Relationship(back_populates="moves")
    player: Optional[Player] = Relationship(back_populates="moves")


# PUBLIC_INTERFACE
class SQLModelBase(SQLModel):
    """Marker class to enable importing metadata for create_all."""
    pass
