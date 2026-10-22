# Deploy the CampusOps backend on Render

The Vercel frontend is already hosted at https://campusops-tau.vercel.app. It requires a separate persistent FastAPI backend.

## Render Blueprint

1. In Render, choose **New → Blueprint** and select the GitHub repository `Shrashti1234/CampusOps`.
2. Review the repository's `render.yaml` and the Starter plan's current pricing **before** approving creation. A persistent disk is required for the existing SQLite database. Render may charge for the service and disk.
3. Deploy the `campusops-api` service. The blueprint generates `JWT_SECRET` and mounts a persistent 1 GB disk at `/data`.
4. Copy the HTTPS URL Render assigns (for example, `https://YOUR-SERVICE.onrender.com`).
5. In Vercel project **campusops → Settings → Environment Variables**, add `VITE_API_URL` with that exact HTTPS backend origin (no trailing slash) for Production and Preview. Redeploy the frontend; Vite embeds the variable at build time.
6. Test `GET /health`, student registration, issue submission, admin status updates and WebSocket updates on the deployed site.

**Important:** The backend is not deployed by committing this blueprint alone. The Blueprint must be approved in Render, and the backend URL must be configured in Vercel.

## Deployment boundaries

- Do not set `DATABASE_URL` to an ephemeral SQLite path. Existing records would be lost on redeploy.
- The Starter service and disk can incur charges. Review costs before enabling.
- Keep the backend as one instance with this SQLite architecture. For multiple instances or high availability, migrate to managed PostgreSQL, add database migrations and distributed event broadcasting.
- Do not put secrets in Vercel's `VITE_` variables; these variables are public in the browser bundle.
- `CAMPUSOPS_CORS_ORIGINS` lists explicit trusted frontend origins. Add any additional production domain to this variable before using it.
- Admin accounts must be created securely by an operator; the public registration endpoint creates students only.
