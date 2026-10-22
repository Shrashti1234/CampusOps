# CampusOps

Campus issue reporting and live resolution workspace. **Milestone 3: authenticated local demo, not production-ready.**

## Features
- React + TypeScript responsive issue board
- Report issues, filter and search, drag cards across the issue board or use status dropdowns
- WebSocket sync between connected tabs
- Optional local sentence-embedding similarity with TF-IDF fallback for duplicate complaints
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

## Optional semantic AI mode

By default the app uses fast, offline TF-IDF matching. To enable more meaning-aware matching, from `backend` install the optional model dependencies:

```bash
pip install -r requirements-ai.txt
```

Set `CAMPUSOPS_SIMILARITY=semantic` in your environment **before** starting FastAPI (PowerShell: `$env:CAMPUSOPS_SIMILARITY="semantic"`; macOS/Linux: `export CAMPUSOPS_SIMILARITY=semantic`). The first use downloads the open-source `all-MiniLM-L6-v2` model, requiring internet and disk space; subsequent matching runs locally. If model loading fails, the API falls back to TF-IDF. The API includes `similarity_engine` to show which method actually ran. Similarity scores are suggestions, not proof that two reports describe the same problem. The pre-submit check only compares a student's own reports to protect other students' information.

## Quick-start local demo with Docker

Install Docker Desktop, then from the repository root:

1. Copy `.env.example` to `.env` and replace `JWT_SECRET` with a strong random secret. Do not commit `.env`.
2. Run `docker compose up --build`.
3. Open `http://localhost:5173`. Register a student account.
4. In a second terminal create an administrator: `docker compose exec backend python create_admin.py admin@example.edu` (password entered interactively).
5. Sign in as admin in another browser profile to see all reports and update their status.

Services bind to **127.0.0.1 only**, not a public interface. SQLite data persists in the named `campusops-data` volume. This compose setup runs Vite's development server; it is **not a production deployment**.

## Demo acceptance checklist

- [ ] Register a student and sign in again after logout
- [ ] Submit a report and confirm it appears under Reported
- [ ] Open a second student account; confirm it cannot see the first student's reports
- [ ] Sign in as an administrator; confirm both students' reports appear
- [ ] Move a report to In Progress, then Resolved; confirm the original student sees updates
- [ ] Preview duplicate reports before submitting a second similar complaint
- [ ] Confirm category analytics and resolution progress update
- [ ] Run `cd backend && python -m pytest -q` and `cd frontend && npm run build`

## Scope and limitations
This is a **local development prototype**, not a production service. Authentication and student/admin roles are implemented, but this is not a hardened production identity system: no email verification, rate limiting, refresh-token rotation, account recovery, or production-grade session revocation. Existing legacy issues without owners are visible only to admins. No file uploads or multi-campus tenant isolation. Do not deploy publicly or submit personal/sensitive complaint data. Semantic matching is optional and not active unless configured. Suggestions are not automatically merged. Drag-and-drop uses browser-native desktop drag events; on touch devices use the status dropdown. Future milestones: secure production migrations, email verification, rate limiting, session management, semantic embeddings, deployment.
