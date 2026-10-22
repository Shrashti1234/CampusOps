# CampusOps

Campus issue reporting and live resolution workspace. **Milestone 1: local demo only.**

## Features
- React + TypeScript responsive issue board
- Report issues, filter and search, change issue status
- WebSocket sync between connected tabs
- TF-IDF + cosine-similarity suggestions for duplicate complaints
- SQLAlchemy persistence using SQLite by default
- FastAPI API docs and backend smoke tests

## Run backend

```bash
cd backend
python -m venv .venv
# Windows PowerShell: .venv\\Scripts\\Activate.ps1
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

## Run frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173; API docs at http://localhost:8000/docs. To run backend tests: `cd backend && python -m pytest -q`.

## Scope and limitations
This is a **local development prototype**, not a production service. No authentication, staff roles, tenant isolation, file uploads, or production-grade WebSocket authorization. Do not deploy publicly or submit personal/sensitive complaint data. Duplicate matching is a TF-IDF baseline, not an LLM or trained semantic embedding model; suggestions are not automatically merged. Status changes use dropdowns; drag-and-drop is a future feature. Future milestones: authentication and roles, secure database isolation, drag-and-drop, semantic embeddings, tests, deployment.
