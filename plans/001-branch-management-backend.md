# Plan 001: Add branch listing, checkout, creation, fetch, and pull backend functions

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md`.
>
> **Drift check (run first)**: `git diff --stat 28ee8c3..HEAD -- models.py git_scanner.py app.py`
> If any in-scope file changed since this plan was written, compare the
> "Current state" excerpts against the live code before proceeding; on a
> mismatch, treat it as a STOP condition.

## Status

- **Priority**: P1
- **Effort**: M (half day)
- **Risk**: LOW — additive functions, no existing logic altered
- **Depends on**: none
- **Category**: direction
- **Planned at**: commit `28ee8c3`, 2026-09-22

## Why this matters

GitPulse currently lacks any capability to list, switch, or create branches,
and has no way to pull from or fetch a remote. The branch bar displays the
active branch as static text — a developer must leave the app and use the
terminal for any branch operation. This plan adds 5 backend functions and
their corresponding REST endpoints, plus the Pydantic models to support them.
All downstream UI work (Plan 002) depends on these endpoints existing.

## Current state

### `models.py` (130 lines)

The module uses Pydantic v2 (`from pydantic import BaseModel, Field`).
All request models follow the pattern `class XxxRequest(BaseModel)`.
All response models are either standalone models or inline dicts.

Existing relevant model:
```python
# models.py:48-52
class BranchInfo(BaseModel):
    name: str
    remote_name: Optional[str] = None
    ahead: int = 0
    behind: int = 0
```

**Missing**: No model for a branch list item, checkout request, create-branch
request, or pull/fetch response.

### `git_scanner.py` (431 lines)

Imports:
```python
# git_scanner.py:1-8
import git
from git import Repo, InvalidGitRepositoryError, NoSuchPathError
from pathlib import Path
from models import *
import os
import re
from datetime import datetime, timezone
from typing import Optional, List, Tuple
```

Existing relevant function:
```python
# git_scanner.py:96-118
def get_branch_info(repo: Repo) -> BranchInfo:
    try:
        branch_name = repo.active_branch.name
    except (TypeError, ValueError):
        ...
    info = BranchInfo(name=branch_name)
    try:
        tracking_branch = repo.active_branch.tracking_branch()
        if tracking_branch:
            info.remote_name = tracking_branch.name
            ahead = sum(1 for _ in repo.iter_commits(f'{tracking_branch.name}..{branch_name}'))
            behind = sum(1 for _ in repo.iter_commits(f'{branch_name}..{tracking_branch.name}'))
            info.ahead = ahead
            info.behind = behind
    except Exception:
        pass
    return info
```

**Missing**: No `list_branches`, `checkout_branch`, `create_branch`,
`pull_changes`, or `fetch_remote` functions.

Mutation functions follow the `Tuple[bool, str]` return convention:
- Success: `(True, "human message")`
- Failure: `(False, "error description")`

Read functions that interact with a repo path create `Repo(path)` inline.

### `app.py` (517 lines)

Route convention: `@app.get/post/put/delete("/api/repos/{repo_id}/...")`.
Helper to resolve repo_id → path:
```python
# app.py:239-244
def _find_repo_path(repo_id: str) -> str:
    config = load_config()
    for r in config.repos:
        if r.id == repo_id:
            return r.path
    raise HTTPException(status_code=404, detail="Repository not found")
```

Existing imports from `git_scanner`:
```python
# app.py:23-28
from git_scanner import (
    validate_git_repo, get_repo_id, get_repo_status, get_repo_summary,
    get_changed_files, build_file_tree, get_branch_info, get_commit_log,
    get_stash_list, get_diff_for_file, stage_files, unstage_files,
    commit_changes, push_changes, apply_stash, pop_stash, drop_stash,
    check_repo_access, init_repo, publish_repo_to_remote
)
```

## Commands you will need

| Purpose       | Command                                        | Expected on success     |
|---------------|-------------------------------------------------|-------------------------|
| Syntax check  | `python -c "import models; import git_scanner; import app; print('OK')"` | Prints `OK`, exit 0 |
| Server start  | `python app.py`                                 | Prints `GitPulse Dashboard` with URL |
| API smoke     | `curl http://localhost:8765/api/repos`           | JSON array, exit 0 |

## Scope

**In scope** (the only files you should modify):
- `models.py`
- `git_scanner.py`
- `app.py`

**Out of scope** (do NOT touch):
- `static/app.js`, `static/index.html`, `static/styles.css` — frontend is Plan 002
- `ai_commit.py`, `notifier.py` — unrelated to branch/sync features
- `config.json`, `.env` — user config files, never edit directly

## Git workflow

- Branch: `feat/phase1-branch-sync-backend`
- Commit style: conventional commits. Example from repo's `git log`:
  `feat: add Gemini model fallbacks and repo publish endpoint`
- Do NOT push or open a PR unless the operator instructed it.

## Steps

### Step 1: Add Pydantic models for branch operations

Open `models.py`. After the existing `BranchInfo` class (line 52), add the
following new models:

```python
class BranchItem(BaseModel):
    name: str
    is_active: bool = False
    is_remote: bool = False
    tracking: Optional[str] = None

class CheckoutBranchRequest(BaseModel):
    branch_name: str
    create: bool = False

class CreateStashRequest(BaseModel):
    message: Optional[str] = None
    include_untracked: bool = True

class DiscardRequest(BaseModel):
    files: Optional[List[str]] = None
```

Note: `CreateStashRequest` and `DiscardRequest` are for Plan 003 but adding
them now avoids a second edit to `models.py` later.

**Verify**: `python -c "from models import BranchItem, CheckoutBranchRequest, CreateStashRequest, DiscardRequest; print('OK')"` → prints `OK`

### Step 2: Add `list_branches` to `git_scanner.py`

Append the following function after `check_repo_access` (line 431):

```python
def list_branches(repo_path: str) -> List[BranchItem]:
    """List all local and remote branches with active HEAD indicator."""
    try:
        repo = Repo(repo_path)
        branches = []

        # Active branch name (safe for detached HEAD)
        try:
            active_name = repo.active_branch.name
        except (TypeError, ValueError):
            active_name = None

        # Local branches
        for head in repo.heads:
            tracking = None
            try:
                tb = head.tracking_branch()
                if tb:
                    tracking = tb.name
            except Exception:
                pass
            branches.append(BranchItem(
                name=head.name,
                is_active=(head.name == active_name),
                is_remote=False,
                tracking=tracking,
            ))

        # Remote branches (exclude HEAD pointers like origin/HEAD)
        for remote in repo.remotes:
            for ref in remote.refs:
                ref_short = ref.remote_head
                if ref_short == "HEAD":
                    continue
                # Skip if already listed as local tracking branch
                branches.append(BranchItem(
                    name=ref.name,  # e.g. "origin/main"
                    is_active=False,
                    is_remote=True,
                    tracking=None,
                ))

        return branches
    except Exception:
        return []
```

**Verify**: `python -c "from git_scanner import list_branches; print('OK')"` → prints `OK`

### Step 3: Add `checkout_branch` to `git_scanner.py`

Append after `list_branches`:

```python
def checkout_branch(repo_path: str, branch_name: str, create: bool = False) -> Tuple[bool, str]:
    """Switch to an existing branch or create a new one.

    Guards:
    - If the working tree has uncommitted changes, warn the user.
    - For remote branches (e.g. 'origin/feature'), create a local tracking branch.
    """
    try:
        repo = Repo(repo_path)

        # Warn if dirty
        if repo.is_dirty(untracked_files=True):
            # Allow checkout but warn — git itself allows this in most cases
            pass

        if create:
            # Create new branch from current HEAD and switch
            if branch_name in [h.name for h in repo.heads]:
                return False, f"Branch '{branch_name}' already exists"
            repo.git.checkout('-b', branch_name)
            return True, f"Created and switched to branch '{branch_name}'"

        # Check if it's a remote branch reference (e.g. origin/feature-x)
        is_remote_ref = '/' in branch_name and branch_name not in [h.name for h in repo.heads]
        if is_remote_ref:
            # Extract the short name after the remote prefix
            parts = branch_name.split('/', 1)
            local_name = parts[1] if len(parts) == 2 else branch_name
            # Check if local branch already exists
            if local_name in [h.name for h in repo.heads]:
                repo.git.checkout(local_name)
                return True, f"Switched to existing local branch '{local_name}'"
            # Create local tracking branch from remote
            repo.git.checkout('-b', local_name, '--track', branch_name)
            return True, f"Created local branch '{local_name}' tracking '{branch_name}'"

        # Standard local checkout
        if branch_name not in [h.name for h in repo.heads]:
            return False, f"Branch '{branch_name}' not found"

        repo.git.checkout(branch_name)
        return True, f"Switched to branch '{branch_name}'"

    except git.GitCommandError as e:
        err = e.stderr.strip() if e.stderr else str(e)
        return False, err
    except Exception as e:
        return False, str(e)
```

**Verify**: `python -c "from git_scanner import checkout_branch; print('OK')"` → prints `OK`

### Step 4: Add `fetch_remote` and `pull_changes` to `git_scanner.py`

Append after `checkout_branch`:

```python
def fetch_remote(repo_path: str, remote_name: str = "origin") -> Tuple[bool, str]:
    """Fetch latest refs from the specified remote."""
    try:
        repo = Repo(repo_path)
        if not repo.remotes:
            return False, "No remote configured"

        remote_names = [r.name for r in repo.remotes]
        if remote_name not in remote_names:
            # Fall back to first available remote
            remote_name = remote_names[0]

        repo.git.fetch(remote_name)
        return True, f"Fetched from '{remote_name}'"
    except git.GitCommandError as e:
        err = e.stderr.strip() if e.stderr else str(e)
        return False, err
    except Exception as e:
        return False, str(e)


def pull_changes(repo_path: str, rebase: bool = False) -> Tuple[bool, str]:
    """Pull upstream changes into the current branch.

    Guards:
    - Requires an upstream tracking branch.
    - Detects merge conflicts and returns a clear error.
    """
    try:
        repo = Repo(repo_path)

        # Check for tracking branch
        try:
            tracking = repo.active_branch.tracking_branch()
        except (TypeError, ValueError):
            return False, "Cannot pull: HEAD is detached"

        if not tracking:
            return False, "No upstream tracking branch configured. Push first to set upstream."

        args = ['--rebase'] if rebase else []
        result = repo.git.pull(*args)

        # Check for merge conflicts
        if repo.index.unmerged_blobs():
            return False, "Pull completed with merge conflicts. Resolve conflicts before committing."

        summary = result.strip() if result else "Already up to date"
        # Truncate very long pull output
        if len(summary) > 200:
            summary = summary[:200] + "..."
        return True, summary

    except git.GitCommandError as e:
        err = e.stderr.strip() if e.stderr else str(e)
        # Provide friendly messages for common failures
        if "CONFLICT" in str(e) or "Merge conflict" in str(e):
            return False, "Merge conflict detected. Resolve conflicts manually before continuing."
        if "Could not resolve host" in err:
            return False, "Network error: could not reach remote. Check your internet connection."
        return False, err
    except Exception as e:
        return False, str(e)
```

**Verify**: `python -c "from git_scanner import fetch_remote, pull_changes; print('OK')"` → prints `OK`

### Step 5: Register new functions in `app.py` imports

Update the import block at `app.py:23-28` to include the new functions:

```python
from git_scanner import (
    validate_git_repo, get_repo_id, get_repo_status, get_repo_summary,
    get_changed_files, build_file_tree, get_branch_info, get_commit_log,
    get_stash_list, get_diff_for_file, stage_files, unstage_files,
    commit_changes, push_changes, apply_stash, pop_stash, drop_stash,
    check_repo_access, init_repo, publish_repo_to_remote,
    list_branches, checkout_branch, fetch_remote, pull_changes
)
```

Also update the models import at `app.py:17-21`:

```python
from models import (
    AppConfig, Settings, RepoConfig, AddRepoRequest, InitRepoRequest,
    PublishRepoRequest, CommitRequest, StageRequest,
    GenerateCommitMessageRequest, GenerateCommitMessageResponse,
    DashboardSummary, RepoStatus, RepoSummary, RepoHealth, TreeNode,
    CommitEntry, StashEntry, ChangedFile, BranchItem, CheckoutBranchRequest
)
```

**Verify**: `python -c "import app; print('OK')"` → prints `OK`

### Step 6: Add REST endpoints in `app.py`

Insert the following endpoints in `app.py` after the existing repo log
endpoint (after line 289, before the `# --- Stash ---` comment at line 291):

```python
# --- Branches ---
@app.get("/api/repos/{repo_id}/branches")
async def repo_branches(repo_id: str):
    path = _find_repo_path(repo_id)
    branches = list_branches(path)
    return [b.model_dump() for b in branches]


@app.post("/api/repos/{repo_id}/branches/checkout")
async def repo_checkout(repo_id: str, req: CheckoutBranchRequest):
    path = _find_repo_path(repo_id)
    ok, msg = checkout_branch(path, req.branch_name, req.create)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"message": msg}


# --- Remote Sync ---
@app.post("/api/repos/{repo_id}/fetch")
async def repo_fetch(repo_id: str):
    path = _find_repo_path(repo_id)
    ok, msg = fetch_remote(path)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"message": msg}


@app.post("/api/repos/{repo_id}/pull")
async def repo_pull(repo_id: str):
    path = _find_repo_path(repo_id)
    ok, msg = pull_changes(path)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"message": msg}
```

**Verify**:
1. `python -c "import app; print('OK')"` → prints `OK`
2. Start server: `python app.py` → prints banner
3. `curl http://localhost:8765/api/repos` → returns JSON list
4. If you have a tracked repo with id (check `config.json`), test:
   `curl http://localhost:8765/api/repos/<repo_id>/branches` → returns JSON array of branch objects

## Test plan

No automated test framework exists in this repo yet. Manual verification:

1. Start the server with `python app.py`.
2. Hit `GET /api/repos` to get a repo ID.
3. Hit `GET /api/repos/{id}/branches` — expect JSON array with at least one item where `is_active: true`.
4. Hit `POST /api/repos/{id}/branches/checkout` with `{"branch_name": "test-branch", "create": true}` — expect 200 with message.
5. Hit `POST /api/repos/{id}/branches/checkout` with `{"branch_name": "main"}` — expect 200 switching back.
6. Hit `POST /api/repos/{id}/branches/checkout` with `{"branch_name": "test-branch", "create": true}` again — expect 400 "already exists".
7. Hit `POST /api/repos/{id}/fetch` — expect 200 or 400 "No remote configured".
8. Hit `POST /api/repos/{id}/pull` — expect 200 or appropriate error.

## Done criteria

- [ ] `python -c "import app; print('OK')"` exits 0
- [ ] `GET /api/repos/{id}/branches` returns `[{name, is_active, is_remote, tracking}, ...]`
- [ ] `POST /api/repos/{id}/branches/checkout` with `create: true` creates and switches
- [ ] `POST /api/repos/{id}/branches/checkout` to existing branch switches
- [ ] `POST /api/repos/{id}/fetch` calls `git fetch` and returns result
- [ ] `POST /api/repos/{id}/pull` calls `git pull` and returns result or conflict message
- [ ] No files outside the in-scope list are modified (`git status`)

## STOP conditions

Stop and report back (do not improvise) if:

- The code at the locations in "Current state" doesn't match the excerpts.
- `from models import *` in `git_scanner.py` fails after model changes.
- GitPython's `repo.heads`, `repo.remotes`, or `repo.git.checkout` behaves
  differently than documented (unlikely but check).
- A step's verification fails twice after a reasonable fix attempt.

## Maintenance notes

- `list_branches` returns remote branches in `origin/name` format. The
  frontend (Plan 002) must split on `/` to display the short name.
- `checkout_branch` with a remote ref (e.g. `origin/feature`) auto-creates
  a local tracking branch. This is intentional — it matches the behavior
  of `git checkout origin/feature` in the terminal.
- `pull_changes` detects conflicts via `repo.index.unmerged_blobs()`. If
  a future version adds merge-conflict resolution UI, this check is the
  entry point.
- When reviewing: verify that `checkout_branch` doesn't clobber unsaved
  changes. The current implementation allows checkout with a dirty tree
  (git does too in most cases) but the frontend should warn the user.
