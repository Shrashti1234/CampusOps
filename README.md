# CampusOps

Campus issue reporting and live resolution workspace. **Milestone 3: authenticated local demo, not production-ready.**

## Features
- React + TypeScript responsive issue board
- Report issues, filter and search, drag cards across the issue board or use status dropdowns
- WebSocket sync between connected tabs
- TF-IDF + cosine-similarity suggestions for duplicate complaints
- SQLAlchemy persistence using SQLite by default
- FastAPI API docs and backend smoke tests
- GitHub Actions CI workflow for backend tests and frontend build
- Student registration/login and admin-only status changes
- Per-student issue visibility and authenticated WebSocket events

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

Create a local admin (from the backend directory):\n\n\`\`\`bash\npython create_admin.py admin@example.edu\n\`\`\`\n\nThe script prompts for a password. Student accounts are created through the frontend; admin accounts are created through the local script. Set a stable, strong \`JWT_SECRET\` environment variable before starting the backend if you want logins to survive restarts.\n\nOpen http://localhost:5173; API docs at http://localhost:8000/docs. To run backend tests: `cd backend && python -m pytest -q`.

## Scope and limitations
This is a **local development prototype**, not a production service. Authentication and student/admin roles are implemented, but this is not a hardened production identity system: no email verification, rate limiting, refresh-token rotation, account recovery, or production-grade session revocation. Existing legacy issues without owners are visible only to admins. No file uploads or multi-campus tenant isolation. Do not deploy publicly or submit personal/sensitive complaint data. Duplicate matching is a TF-IDF baseline, not an LLM or trained semantic embedding model; suggestions are not automatically merged. Drag-and-drop uses browser-native desktop drag events; on touch devices use the status dropdown. Future milestones: secure production migrations, email verification, rate limiting, session management, semantic embeddings, deployment.
