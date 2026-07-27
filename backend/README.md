# Backend

```powershell
. ..\scripts\enable-proxy.ps1
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
$env:DATABASE_URL="sqlite+aiosqlite:///./dev.db"
python -m app.bootstrap
uvicorn app.main:app --reload
```

This repository's isolated environment is `backend/.venv`. If PowerShell already has another
virtual environment activated, run commands as `.\.venv\Scripts\python.exe -I -m <module>`.
