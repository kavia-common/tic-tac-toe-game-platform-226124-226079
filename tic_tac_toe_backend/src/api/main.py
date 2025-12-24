from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session

from src.db.database import init_db, get_session

openapi_tags = [
    {"name": "health", "description": "Service health checks"},
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


# Example of using session dependency (for future endpoints)
def _example_dep(session: Session = Depends(get_session)) -> str:
    """Internal example dependency that uses DB session; not exposed as endpoint."""
    return "ok"
