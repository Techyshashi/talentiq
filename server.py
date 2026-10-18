"""TalentIQ web API. Run with: uvicorn server:app --reload."""
from __future__ import annotations

import csv
import io
import json
import os
import secrets
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

import ai_core
import parsing
from sessions import create_job, create_session, delete_session, get_job, get_session

app = FastAPI(title="TalentIQ", version="1.0")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:8000", "http://127.0.0.1:8000"],
                   allow_credentials=False, allow_methods=["GET", "POST"],
                   allow_headers=["Authorization", "Content-Type"])
executor = ThreadPoolExecutor(max_workers=4)


@app.middleware("http")
async def security_headers(request, call_next):
    response = await call_next(request)
    response.headers.update({"X-Content-Type-Options": "nosniff", "X-Frame-Options": "DENY",
                             "Referrer-Policy": "no-referrer",
                             "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; object-src 'none'; frame-ancestors 'none'"})
    return response


def require_auth(authorization: str | None = Header(default=None)):
    token = authorization.removeprefix("Bearer ").strip() if authorization else None
    session = get_session(token)
    if not session:
        raise HTTPException(401, detail={"code": "AUTH_REQUIRED", "message": "Sign in to continue."})
    return token, session


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=200)


class TextRequest(BaseModel):
    text: str = Field(min_length=1, max_length=50_000)


class JDRequest(BaseModel):
    jd: dict[str, Any]


class MarketRequest(BaseModel):
    jd: dict[str, Any]
    posts: str = Field(default="", max_length=50_000)


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "TalentIQ", "ai_configured": bool(ai_core.DEPLOYMENT)}


@app.post("/api/login")
def login(payload: LoginRequest):
    expected_username = os.getenv("APP_USERNAME")
    expected_password = os.getenv("APP_PASSWORD")
    if not expected_username or not expected_password:
        raise HTTPException(500, detail={"code": "CONFIGURATION_ERROR", "message": "APP_USERNAME and APP_PASSWORD are not configured."})
    if not secrets.compare_digest(payload.username, expected_username) or not secrets.compare_digest(payload.password, expected_password):
        raise HTTPException(401, detail={"code": "INVALID_CREDENTIALS", "message": "Invalid username or password."})
    return {"token": create_session(payload.username), "expires_in": 4 * 60 * 60, "username": payload.username}


@app.post("/api/logout")
def logout(auth=Depends(require_auth)):
    delete_session(auth[0])
    return {"ok": True}


def ai_error(exc: Exception) -> HTTPException:
    return HTTPException(502, detail={"code": "AI_ERROR", "message": str(exc)})


@app.post("/api/jd/analyse")
async def analyse_jd(text: str = Form(""), file: UploadFile | None = File(None), auth=Depends(require_auth)):
    try:
        if file:
            data = await file.read()
            parsing.validate_upload(file.filename or "", data)
            text = parsing.extract_text(file.filename or "", data)
        if not text.strip():
            raise HTTPException(400, detail={"code": "EMPTY_JD", "message": "Provide JD text or a file."})
        return {"jd": ai_core.ask(ai_core.JD_SYSTEM, text, as_json=True), "text": text[:50_000]}
    except HTTPException:
        raise
    except Exception as exc:
        raise ai_error(exc) from exc


@app.post("/api/cvs/upload")
async def upload_cvs(files: list[UploadFile] = File(...), auth=Depends(require_auth)):
    if len(files) > 100:
        raise HTTPException(400, detail={"code": "TOO_MANY_FILES", "message": "Upload at most 100 CVs."})
    cvs, failed = [], []
    for file in files:
        try:
            data = await file.read()
            parsing.validate_upload(file.filename or "", data, cv=True)
            text = parsing.extract_text(file.filename or "", data)
            cvs.append({"filename": file.filename, "text": text, "characters": len(text), "readable": bool(text)})
        except Exception as exc:
            failed.append({"filename": file.filename, "error": str(exc)})
    return {"cvs": cvs, "failed": failed}


def rank_cv(jd: dict[str, Any], cv: dict[str, Any]) -> dict[str, Any]:
    if not cv["text"]:
        return {"filename": cv["filename"], "score": 0, "reason": "No readable text was extracted.", "matched_skills": [], "missing_skills": [], "evidence": ""}
    result = ai_core.ask(ai_core.RANK_SYSTEM, f"JOB REQUIREMENTS:\n{json.dumps(jd)}\n\nCV TEXT:\n{cv['text'][:12000]}", as_json=True)
    result["filename"] = cv["filename"]
    result["score"] = max(0, min(100, int(result.get("score", 0))))
    return result


@app.post("/api/ranking/start")
def start_ranking(payload: dict[str, Any], auth=Depends(require_auth)):
    jd, cvs = payload.get("jd"), payload.get("cvs", [])
    if not isinstance(jd, dict) or not cvs:
        raise HTTPException(400, detail={"code": "MISSING_INPUT", "message": "Provide an analysed JD and CVs."})
    job_id, job = create_job(len(cvs))
    def work():
        job.status = "running"
        futures = [executor.submit(rank_cv, jd, cv) for cv in cvs]
        try:
            for future in as_completed(futures):
                try:
                    job.results.append(future.result())
                except Exception as exc:
                    job.results.append({"filename": "unknown", "score": 0, "reason": str(exc)})
                job.completed += 1
            job.results.sort(key=lambda row: row.get("score", 0), reverse=True)
            job.status = "completed"
        except Exception as exc:
            job.status, job.error = "failed", str(exc)
    executor.submit(work)
    return {"job_id": job_id}


@app.get("/api/ranking/{job_id}")
def ranking_status(job_id: str, auth=Depends(require_auth)):
    job = get_job(job_id)
    if not job:
        raise HTTPException(404, detail={"code": "NOT_FOUND", "message": "Ranking job not found."})
    return {"status": job.status, "total": job.total, "completed": job.completed, "results": job.results if job.status in ("completed", "failed") else [], "error": job.error}


@app.post("/api/questions")
def questions(payload: JDRequest, auth=Depends(require_auth)):
    try:
        return ai_core.ask(ai_core.QUESTIONS_SYSTEM, json.dumps(payload.jd), as_json=True)
    except Exception as exc:
        raise ai_error(exc) from exc


@app.post("/api/market")
def market(payload: MarketRequest, auth=Depends(require_auth)):
    try:
        prompt = (
            f"ROLE DETAILS:\n{json.dumps(payload.jd)}\n\n"
            f"PUBLIC JOB POSTS SUPPLIED:\n{payload.posts or 'NONE'}"
        )
        return ai_core.ask(ai_core.MARKET_SYSTEM, prompt, as_json=True)
    except Exception as exc:
        raise ai_error(exc) from exc


@app.post("/api/search")
def search(payload: JDRequest, auth=Depends(require_auth)):
    try:
        return ai_core.ask(ai_core.SEARCH_SYSTEM, json.dumps(payload.jd), as_json=True)
    except Exception as exc:
        raise ai_error(exc) from exc


@app.post("/api/ranking/{job_id}/csv")
def export_csv(job_id: str, auth=Depends(require_auth)):
    job = get_job(job_id)
    if not job or job.status != "completed":
        raise HTTPException(404, detail={"code": "NOT_READY", "message": "Ranking is not ready."})
    output = io.StringIO()
    rows = job.results
    fields = ["filename", "score", "reason", "matched_skills", "missing_skills", "evidence"]
    writer = csv.DictWriter(output, fieldnames=fields)
    writer.writeheader()
    for row in rows:
        writer.writerow({field: ", ".join(row[field]) if isinstance(row.get(field), list) else row.get(field, "") for field in fields})
    return StreamingResponse(iter([output.getvalue()]), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=talentiq-ranking.csv"})


ROOT = Path(__file__).parent
app.mount("/", StaticFiles(directory=str(ROOT / "web"), html=True), name="web")
