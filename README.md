# tic-tac-toe-game-platform-226124-226079

Backend environment configuration (FastAPI):
- CORS_ORIGINS: Comma-separated list of frontend origins allowed by CORS. Defaults to http://localhost:3000. Use "*" to allow any origin (dev only).
- TICTACTOE_DB_PATH: Filesystem path to the SQLite DB file. Defaults to ./data/tictactoe.db if not set. DB_PATH is also supported for backward compatibility.

Usage:
1) Copy .env.example to .env and adjust values if needed.
2) Start the backend (default port 3001; do not change ports per project constraints).
3) The React frontend is expected to call the backend using REACT_APP_API_BASE_URL default http://localhost:3001.

OpenAPI:
- The API docs are available at /docs.
- To update the interfaces/openapi.json file after code changes, run the generator module that imports the app:
  python -m src.api.generate_openapi
This writes interfaces/openapi.json with the latest schema.