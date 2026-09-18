"""
GitPulse — FastAPI Application
Multi-Repo Git Tracking Dashboard
"""

import json
import sys
import os
from pathlib import Path
from typing import Optional, List
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

from models import (
    AppConfig, Settings, RepoConfig, AddRepoRequest, CommitRequest,
    StageRequest, GenerateCommitMessageRequest, GenerateCommitMessageResponse,
    DashboardSummary, RepoStatus, RepoSummary, RepoHealth, TreeNode,
    CommitEntry, StashEntry, ChangedFile
)
from git_scanner import (
    validate_git_repo, get_repo_id, get_repo_status, get_repo_summary,
    get_changed_files, build_file_tree, get_branch_info, get_commit_log,
    get_stash_list, get_diff_for_file, stage_files, unstage_files,
    commit_changes, push_changes, apply_stash, pop_stash, drop_stash,
    check_repo_access
)
from ai_commit import generate_commit_message
from notifier import NotificationManager, NotificationScheduler
from git import Repo

# --- Config ---
CONFIG_PATH = Path(__file__).parent / "config.json"
CONFIG_EXAMPLE_PATH = Path(__file__).parent / "config.example.json"


def load_config() -> AppConfig:
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "r") as f:
            data = json.load(f)
        return AppConfig(**data)
    elif CONFIG_EXAMPLE_PATH.exists():
        with open(CONFIG_EXAMPLE_PATH, "r") as f:
            data = json.load(f)
        cfg = AppConfig(**data)
        save_config(cfg)
        return cfg
    cfg = AppConfig(repos=[], settings=Settings())
    save_config(cfg)
    return cfg


def save_config(config: AppConfig):
    with open(CONFIG_PATH, "w") as f:
        json.dump(config.model_dump(), f, indent=2)


# --- Lifespan ---
notification_manager: Optional[NotificationManager] = None
notification_scheduler: Optional[NotificationScheduler] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global notification_manager, notification_scheduler
    config = load_config()
    notification_manager = NotificationManager(str(CONFIG_PATH))
    notification_scheduler = NotificationScheduler(str(CONFIG_PATH))

    def scan_repos():
        cfg = load_config()
        summaries = []
        for r in cfg.repos:
            try:
                s = get_repo_summary(r.path, cfg.settings.staleness_threshold_days)
                summaries.append(s.model_dump())
            except Exception:
                pass
        return summaries

    notification_scheduler.start(scan_repos, config.settings.auto_refresh_seconds * 5)
    yield
    notification_scheduler.stop()


# --- App ---
app = FastAPI(
    title="GitPulse",
    description="Multi-Repo Git Tracking Dashboard",
    version="1.0.0",
    lifespan=lifespan,
)

# Serve static files
static_dir = Path(__file__).parent / "static"

@app.middleware("http")
async def add_no_cache_headers(request, call_next):
    response = await call_next(request)
    if request.url.path.startswith("/static") or request.url.path == "/":
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response

if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


# --- Root ---
@app.get("/")
async def root():
    index_path = static_dir / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return {"message": "GitPulse API is running. Visit /docs for API documentation."}


# --- Dashboard ---
@app.get("/api/dashboard", response_model=DashboardSummary)
async def get_dashboard():
    config = load_config()
    summaries = []
    for r in config.repos:
        try:
            s = get_repo_summary(r.path, config.settings.staleness_threshold_days)
            summaries.append(s)
        except Exception as e:
            summaries.append(RepoSummary(
                id=r.id, name=Path(r.path).name, path=r.path,
                branch_name="unknown", health=RepoHealth.DIRTY,
                changed_count=0, untracked_count=0, unpushed_count=0,
                stash_count=0, last_commit_time=None,
                last_commit_message=f"Error: {str(e)}"
            ))

    needing_attention = sum(1 for s in summaries if s.health != RepoHealth.CLEAN)
    with_unpushed = sum(1 for s in summaries if s.unpushed_count > 0)
    stale = sum(1 for s in summaries if s.health == RepoHealth.STALE)

    return DashboardSummary(
        total_repos=len(summaries),
        repos_needing_attention=needing_attention,
        repos_with_unpushed=with_unpushed,
        stale_repos=stale,
        repo_summaries=summaries
    )


# --- Repos CRUD ---
@app.get("/api/repos", response_model=List[RepoSummary])
async def list_repos():
    config = load_config()
    summaries = []
    for r in config.repos:
        try:
            summaries.append(get_repo_summary(r.path, config.settings.staleness_threshold_days))
        except Exception:
            pass
    return summaries


@app.post("/api/repos")
async def add_repo(req: AddRepoRequest):
    path = req.path.strip()
    is_valid, err = validate_git_repo(path)
    if not is_valid:
        raise HTTPException(status_code=400, detail=f"Invalid git repository: {err}")

    config = load_config()
    repo_id = get_repo_id(path)

    # Check for duplicates
    for r in config.repos:
        if os.path.normpath(r.path) == os.path.normpath(path):
            raise HTTPException(status_code=409, detail="Repository already tracked")

    # Check access
    has_access, access_msg = check_repo_access(path)
    if not has_access:
        raise HTTPException(status_code=403, detail=f"Access denied: {access_msg}")

    config.repos.append(RepoConfig(id=repo_id, path=path))
    save_config(config)

    summary = get_repo_summary(path, config.settings.staleness_threshold_days)
    return {"message": "Repository added", "repo": summary.model_dump()}


@app.delete("/api/repos/{repo_id}")
async def remove_repo(repo_id: str):
    config = load_config()
    original_count = len(config.repos)
    config.repos = [r for r in config.repos if r.id != repo_id]

    if len(config.repos) == original_count:
        raise HTTPException(status_code=404, detail="Repository not found")

    save_config(config)
    return {"message": "Repository removed"}


# --- Repo Detail ---
def _find_repo_path(repo_id: str) -> str:
    config = load_config()
    for r in config.repos:
        if r.id == repo_id:
            return r.path
    raise HTTPException(status_code=404, detail="Repository not found")


@app.get("/api/repos/{repo_id}/status")
async def repo_status(repo_id: str):
    path = _find_repo_path(repo_id)
    try:
        status = get_repo_status(path)
        return status.model_dump()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/repos/{repo_id}/tree")
async def repo_tree(repo_id: str):
    path = _find_repo_path(repo_id)
    try:
        repo = Repo(path)
        changed_files = get_changed_files(repo)
        tree = build_file_tree(changed_files)
        return [node.model_dump() for node in tree]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/repos/{repo_id}/diff")
async def repo_diff(repo_id: str, file: str = Query(...)):
    path = _find_repo_path(repo_id)
    try:
        repo = Repo(path)
        diff = get_diff_for_file(repo, file)
        return {"file": file, "diff": diff}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/repos/{repo_id}/log")
async def repo_log(repo_id: str, count: int = Query(15)):
    path = _find_repo_path(repo_id)
    try:
        repo = Repo(path)
        commits = get_commit_log(repo, count)
        return [c.model_dump() for c in commits]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Stash ---
@app.get("/api/repos/{repo_id}/stash")
async def repo_stash(repo_id: str):
    path = _find_repo_path(repo_id)
    try:
        repo = Repo(path)
        stashes = get_stash_list(repo)
        return [s.model_dump() for s in stashes]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/repos/{repo_id}/stash/apply")
async def stash_apply(repo_id: str, index: int = Query(0)):
    path = _find_repo_path(repo_id)
    ok, msg = apply_stash(path, index)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"message": msg}


@app.post("/api/repos/{repo_id}/stash/pop")
async def stash_pop(repo_id: str, index: int = Query(0)):
    path = _find_repo_path(repo_id)
    ok, msg = pop_stash(path, index)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"message": msg}


@app.delete("/api/repos/{repo_id}/stash/{index}")
async def stash_drop(repo_id: str, index: int):
    path = _find_repo_path(repo_id)
    ok, msg = drop_stash(path, index)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"message": msg}


# --- Stage / Unstage ---
@app.post("/api/repos/{repo_id}/stage")
async def stage(repo_id: str, req: StageRequest):
    path = _find_repo_path(repo_id)
    ok = stage_files(path, req.files)
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to stage files")
    return {"message": "Files staged"}


@app.post("/api/repos/{repo_id}/unstage")
async def unstage(repo_id: str, req: StageRequest):
    path = _find_repo_path(repo_id)
    ok = unstage_files(path, req.files)
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to unstage files")
    return {"message": "Files unstaged"}


# --- Commit / Push ---
@app.post("/api/repos/{repo_id}/commit")
async def commit(repo_id: str, req: CommitRequest):
    path = _find_repo_path(repo_id)

    # Verify access
    has_access, access_msg = check_repo_access(path)
    if not has_access:
        raise HTTPException(status_code=403, detail=f"Access denied: {access_msg}")

    ok, result = commit_changes(path, req.message, req.files)
    if not ok:
        raise HTTPException(status_code=400, detail=result)
    return {"message": "Committed", "commit_hash": result}


@app.post("/api/repos/{repo_id}/push")
async def push(repo_id: str):
    path = _find_repo_path(repo_id)

    # Verify access
    has_access, access_msg = check_repo_access(path)
    if not has_access:
        raise HTTPException(status_code=403, detail=f"Access denied: {access_msg}")

    ok, result = push_changes(path)
    if not ok:
        raise HTTPException(status_code=400, detail=result)
    return {"message": result}


@app.post("/api/repos/{repo_id}/commit-push")
async def commit_and_push(repo_id: str, req: CommitRequest):
    path = _find_repo_path(repo_id)

    # Verify access
    has_access, access_msg = check_repo_access(path)
    if not has_access:
        raise HTTPException(status_code=403, detail=f"Access denied: {access_msg}")

    ok, result = commit_changes(path, req.message, req.files)
    if not ok:
        raise HTTPException(status_code=400, detail=f"Commit failed: {result}")

    ok_push, push_result = push_changes(path)
    if not ok_push:
        return {"message": f"Committed ({result}) but push failed: {push_result}", "commit_hash": result, "push_failed": True}

    return {"message": "Committed and pushed", "commit_hash": result}


# --- AI Commit Message ---
@app.post("/api/ai/generate-commit", response_model=GenerateCommitMessageResponse)
async def ai_generate_commit(req: GenerateCommitMessageRequest):
    path = _find_repo_path(req.repo_id)
    try:
        repo = Repo(path)
        config = load_config()
        provider = config.settings.ai_provider or "gemini"

        # Resolve API key from settings if provided
        api_key = None
        if provider == "gemini" and config.settings.gemini_api_key:
            api_key = config.settings.gemini_api_key
        elif provider == "openai" and config.settings.openai_api_key:
            api_key = config.settings.openai_api_key

        target_files = req.files if req.files else None

        diff_parts = []
        try:
            diff_cached = repo.git.diff('--cached', *(target_files or []))
            if diff_cached:
                diff_parts.append(diff_cached)
        except Exception:
            pass

        try:
            diff_working = repo.git.diff(*(target_files or []))
            if diff_working:
                diff_parts.append(diff_working)
        except Exception:
            pass

        # Untracked files
        untracked = [f for f in repo.untracked_files if not target_files or f in target_files]
        if untracked:
            diff_parts.append("New untracked files:\n" + "\n".join(f"  + {f}" for f in untracked))

        diff_text = "\n\n".join(diff_parts)

        # File list
        if target_files:
            all_changed_files = target_files
        else:
            changed_entries = get_changed_files(path)
            all_changed_files = [f.path for f in changed_entries]

        if not diff_text and not all_changed_files:
            raise HTTPException(status_code=400, detail="No changes to generate message for")

        message, used_provider = generate_commit_message(
            diff_text=diff_text,
            provider=provider,
            api_key=api_key,
            changed_files=all_changed_files
        )
        return GenerateCommitMessageResponse(message=message, provider=used_provider)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Settings ---
@app.get("/api/settings")
async def get_settings():
    config = load_config()
    return config.settings.model_dump()


@app.put("/api/settings")
async def update_settings(settings: Settings):
    config = load_config()
    config.settings = settings
    save_config(config)
    return {"message": "Settings updated", "settings": settings.model_dump()}


# --- Notifications ---
@app.get("/api/notifications")
async def get_notifications():
    if notification_manager:
        return notification_manager.get_pending_notifications()
    return []


@app.post("/api/notifications/{notification_id}/read")
async def mark_notification_read(notification_id: str):
    if notification_manager:
        notification_manager.clear_notification(notification_id)
    return {"message": "Notification marked as read"}


# --- Run ---
if __name__ == "__main__":
    import uvicorn
    print("\n  >> GitPulse Dashboard")
    print("  --------------------------------------")
    print("  Local URL:  http://localhost:8765")
    print("  API Docs:   http://localhost:8765/docs")
    print("  --------------------------------------\n")
    uvicorn.run(app, host="127.0.0.1", port=8765, log_level="info")
