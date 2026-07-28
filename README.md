# Open AI Workflow

Open AI Workflow is a self-hosted, multi-workspace AI workflow platform built with Python and Vue. It provides a visual workflow designer, versioned Python scripts, OpenAI-compatible models, queued execution, streaming run events, and application publishing.

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

## Python scripts

The script library supports built-in templates, Monaco editing, visual input/output parameters,
advanced JSON Schema, unsaved-draft tests, streamed logs, cancellation, version diff, and restore.
Uploaded ZIP bundles may contain up to 100 UTF-8 `.py` files (5 MB total). Package directories and
`__init__.py` files are preserved, so standard imports work between files. Use a module entrypoint
such as `main:main` or `package.module:main`; when a ZIP contains exactly one function named `main`,
the upload API can infer its module automatically. Script entrypoints must return a JSON object.

Script tests run asynchronously. `POST .../scripts/test` or `POST .../scripts/{id}/test` returns a
task ID; consume `GET .../scripts/tests/{task_id}/events` for status, logs, and the final result, or
cancel it through `POST .../scripts/tests/{task_id}/cancel`.

## Services

- `web`: Vue 3, PrimeVue Volt, Tailwind CSS, Vue Flow
- `api`: FastAPI management and published-app APIs
- `worker`: Celery workflow execution and scheduled-run dispatch
- `sandbox`: restricted Python script execution service
- PostgreSQL with pgvector, Redis, and MinIO

The retired knowledge-base and document-node features are not part of the default stack. A legacy
`document-worker` image remains behind the optional `document` Compose profile for migration and
compatibility work only; new document nodes cannot be added from the product UI.

## Database migrations

The API container runs `alembic upgrade head` before startup. For local backend development, run:

```powershell
Set-Location backend
alembic upgrade head
```

Create schema changes with `alembic revision --autogenerate -m "change"`; do not use
`Base.metadata.create_all` to update a deployed database.

## Operations

- `GET /metrics` exposes Prometheus request metrics and worker node counters.
- Every API response includes `X-Request-ID`; application logs are JSON and include the same ID.
- Set `OTEL_EXPORTER_OTLP_ENDPOINT` to export API and worker traces through OTLP/HTTP.
- Set `ALERT_WEBHOOK_URL` to receive JSON notifications for workflow failures and unhandled API errors.
- Full workflow runs are queued. The create-run response is initially `pending`; consume the run
  event endpoint for token/node events and fetch the run detail after its terminal event.

## Security defaults

Script execution is disabled unless the sandbox service is available. The sandbox runs as a
non-root user, uses a restricted Docker API proxy, and starts runtime containers with no Linux
capabilities, a root-owned application filesystem, a private writable `/tmp` mount,
PID/memory/CPU limits, and networking disabled by
default. Each execution is staged in its own ephemeral container layer; jobs do not share a volume.
The sandbox uses a distinct `SANDBOX_SHARED_SECRET` and cannot reach the database, Redis, or MinIO
networks. PostgreSQL, Redis, MinIO, and the sandbox API are internal-only Compose services.
`MAX_REQUEST_BODY_BYTES` limits fixed-length and chunked request bodies before parsing.
Credentials are encrypted at rest and never returned by API responses. Workspace authorization is
enforced server-side for every scoped resource. Replace every example secret before deployment.
