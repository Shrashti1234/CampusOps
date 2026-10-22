# CampusOps

Campus issue reporting and live resolution workspace. **Milestone 1: local demo only.**

## Features
- React + TypeScript responsive issue board
- Report issues, filter and search, drag cards across the issue board or use status dropdowns
- WebSocket sync between connected tabs
- TF-IDF + cosine-similarity suggestions for duplicate complaints
- SQLAlchemy persistence using SQLite by default
- FastAPI API docs and backend smoke tests
- GitHub Actions CI workflow for backend tests and frontend build

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
This is a **local development prototype**, not a production service. No authentication, staff roles, tenant isolation, file uploads, or production-grade WebSocket authorization. Do not deploy publicly or submit personal/sensitive complaint data. Duplicate matching is a TF-IDF baseline, not an LLM or trained semantic embedding model; suggestions are not automatically merged. Drag-and-drop uses browser-native desktop drag events; on touch devices use the status dropdown. Future milestones: authentication and roles, secure database isolation, semantic embeddings, tests, deployment.
