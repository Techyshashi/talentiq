---
title: TalentIQ Web
description: Setup and run instructions for the FastAPI and vanilla JavaScript TalentIQ wizard
---

# TalentIQ Web

The web app preserves the existing Streamlit app and uses the same Azure configuration in
`.env`.

Install the web requirements with:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-web.txt
```

Start the API and static frontend with:

```powershell
.\.venv\Scripts\python.exe -m uvicorn server:app --host 127.0.0.1 --port 8000
```

Open <http://127.0.0.1:8000>. Configure `APP_USERNAME`, `APP_PASSWORD`, and the existing
Azure variables before using AI features. Tokens are in-memory and expire after four hours;
uploaded documents are processed in memory and are not persisted.

The API health check is available at <http://127.0.0.1:8000/api/health>.
