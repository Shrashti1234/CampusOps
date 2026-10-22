# CampusOps demo and release checklist

## Current release scope

CampusOps is a local, authenticated portfolio MVP. Its Docker Compose configuration binds services to loopback addresses and runs a Vite development server. It is not a public production deployment.

## Automated verification

The GitHub Actions workflow runs:
1. FastAPI backend unit and permission tests.
2. React/TypeScript frontend build.
3. Docker Compose HTTP smoke tests covering student registration, authorization, admin status changes, and student isolation.
4. Playwright Chromium browser test for student registration and issue submission.

A successful backend/frontend build alone does **not** establish browser E2E success. Inspect the latest GitHub Actions run and download Playwright failure evidence when browser checks fail.

## Manual demonstration

1. Copy `.env.example` to `.env` and replace `JWT_SECRET` with a strong secret.
2. Run `docker compose up --build`.
3. Visit `http://localhost:5173` and register a student.
4. Submit a complaint; use the duplicate-preview button on a second similar report.
5. Create an administrator in a separate terminal: `docker compose exec backend python create_admin.py admin@example.edu`.
6. Sign in as admin in another browser profile, change the issue to In progress and Resolved, and verify the student's board updates.
7. Check search, category filters, analytics, mobile layout, and logout/login.

## Before public deployment

- Choose a host and persistent managed database; SQLite on ephemeral storage will lose data after instance replacement.
- Set strong secret values through the host's secret manager; never commit `.env`.
- Serve a built frontend through a production static server rather than Vite dev mode.
- Configure frontend API URL, secure HTTPS/WSS, and narrowly scoped CORS origins for the actual hostnames.
- Add rate limiting, account recovery, email verification, robust token revocation, migrations, and operational monitoring.
- Re-run backend, browser, and security checks against the deployed staging environment.
- Avoid real names, personal details, or sensitive complaint data in public demo accounts.

No public URL exists until hosting is configured and deployed.
