"""In-memory authentication and background job state."""
from __future__ import annotations

import secrets
import time
from dataclasses import dataclass, field
from typing import Any

TOKEN_TTL = 4 * 60 * 60


@dataclass
class Session:
    username: str
    expires_at: float


@dataclass
class Job:
    status: str = "queued"
    total: int = 0
    completed: int = 0
    results: list[dict[str, Any]] = field(default_factory=list)
    error: str | None = None


_sessions: dict[str, Session] = {}
_jobs: dict[str, Job] = {}


def create_session(username: str) -> str:
    token = secrets.token_urlsafe(32)
    _sessions[token] = Session(username, time.time() + TOKEN_TTL)
    return token


def get_session(token: str | None) -> Session | None:
    if not token:
        return None
    session = _sessions.get(token)
    if not session or session.expires_at <= time.time():
        _sessions.pop(token, None)
        return None
    return session


def delete_session(token: str | None) -> None:
    if token:
        _sessions.pop(token, None)


def create_job(total: int) -> tuple[str, Job]:
    job_id = secrets.token_urlsafe(18)
    job = Job(total=total)
    _jobs[job_id] = job
    return job_id, job


def get_job(job_id: str) -> Job | None:
    return _jobs.get(job_id)
