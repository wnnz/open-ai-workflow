# Open AI Workflow

Open AI Workflow is a self-hosted, multi-workspace AI workflow platform built with Python and Vue. It provides a visual workflow designer, versioned Python scripts, OpenAI-compatible models, document processing, knowledge bases, and Dify-style publishing.

## Quick start

1. Copy `.env.example` to `.env` and replace the secrets.
2. Enable the local dependency proxy when needed:

   ```powershell
   .\scripts\enable-proxy.ps1
   ```

3. Start the stack:

   ```powershell
   docker compose up --build
   ```

4. Open <http://localhost:5173>. API documentation is available at <http://localhost:8000/docs>.

For local development without containers, see `backend/README.md` and `frontend/README.md`.

## Local Python environment

The backend has its own virtual environment at `backend/.venv`. On Windows, use it without
activating any other project environment:

```powershell
.\scripts\enable-proxy.ps1
& .\backend\.venv\Scripts\python.exe -I -m pytest .\backend\tests
& .\backend\.venv\Scripts\python.exe -I -m uvicorn app.main:app --app-dir .\backend --reload
```

The `-I` flag prevents packages from another Python environment leaking into this project.

## Published application API

Publishing freezes the workflow graph and script version references. A publication can be
`public` or `protected`. Protected applications use workspace-managed Bearer keys:

```text
POST /api/v1/workspaces/{workspace_id}/api-keys
POST /v1/apps/{app_slug}/run
Authorization: Bearer owf_...
```

The key value is returned only when it is created; list responses expose only its prefix.

## Services

- `web`: Vue 3, PrimeVue Volt, Tailwind CSS, Vue Flow
- `api`: FastAPI management and published-app APIs
- `worker`: Celery workflow and indexing jobs
- `document-worker`: isolated Office/PDF processing image
- `sandbox`: restricted Python script execution service
- PostgreSQL with pgvector, Redis, and MinIO

## Security defaults

Script execution is disabled unless the sandbox service is available. Runtime containers are network-isolated by default. Credentials are encrypted at rest and never returned by API responses. Workspace authorization is enforced server-side for every scoped resource.
