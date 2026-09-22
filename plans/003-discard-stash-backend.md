# Plan 003: Add discard changes, stash creation backend & REST endpoints

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md`.
>
> **Drift check (run first)**: `git diff --stat 28ee8c3..HEAD -- git_scanner.py app.py models.py`
> If any in-scope file changed since this plan was written, compare the
> "Current state" excerpts against the live code before proceeding; on a
> mismatch, treat it as a STOP condition.

## Status

- **Priority**: P1
- **Effort**: M (half day)
- **Risk**: MED — discard operations are destructive; must guard carefully
- **Depends on**: `plans/001-branch-management-backend.md` (for models)
- **Category**: direction
- **Planned at**: commit `28ee8c3`, 2026-09-22

## Why this matters

Developers frequently need to discard unwanted changes (reverting modified
files or cleaning untracked files) and stash work-in-progress before switching
branches or pulling. GitPulse currently has backend endpoints to apply, pop,
and drop stashes, but **cannot create stashes** and has **no way to discard
working tree changes**. Without these, developers must leave the app for the
terminal.

Discard operations are destructive and unrecoverable (unlike git commits).
This plan implements them with extra safety: distinct handling for tracked
(modified) vs. untracked files, and clear error messages.

## Current state

### `git_scanner.py` — relevant mutation functions

All mutation functions follow `Tuple[bool, str]` pattern:

```python
# git_scanner.py:296-302
def unstage_files(repo_path: str, files: List[str]) -> bool:
    try:
        repo = Repo(repo_path)
        repo.git.restore('--staged', *files)
        return True
    except Exception:
        return False
```

```python
# git_scanner.py:399-421
def apply_stash(repo_path: str, index: int = 0) -> Tuple[bool, str]:
    try:
        repo = Repo(repo_path)
        repo.git.stash('apply', f'stash@{{{index}}}')
        return True, "Stash applied"
    except Exception as e:
        return False, str(e)

def pop_stash(repo_path: str, index: int = 0) -> Tuple[bool, str]:
    ...

def drop_stash(repo_path: str, index: int) -> Tuple[bool, str]:
    ...
```

**Missing**: `discard_file_changes`, `discard_all_changes`, `create_stash`.

### `models.py` — existing request models

If Plan 001 has been executed, `CreateStashRequest` and `DiscardRequest`
already exist. If NOT, you must add them:

```python
class CreateStashRequest(BaseModel):
    message: Optional[str] = None
    include_untracked: bool = True

class DiscardRequest(BaseModel):
    files: Optional[List[str]] = None
```

### `app.py` — existing stash endpoints (lines 291-327)

```python
# app.py:291-327
# --- Stash ---
@app.get("/api/repos/{repo_id}/stash")
async def repo_stash(repo_id: str):
    ...

@app.post("/api/repos/{repo_id}/stash/apply")
async def stash_apply(repo_id: str, index: int = Query(0)):
    ...

@app.post("/api/repos/{repo_id}/stash/pop")
async def stash_pop(repo_id: str, index: int = Query(0)):
    ...

@app.delete("/api/repos/{repo_id}/stash/{index}")
async def stash_drop(repo_id: str, index: int):
    ...
```

**Missing**: `POST /api/repos/{repo_id}/stash` (create) and
`POST /api/repos/{repo_id}/discard` (discard changes).

### `app.py` — imports from `git_scanner` (lines 23-28)

After Plan 001, these include `list_branches, checkout_branch, fetch_remote,
pull_changes`. If Plan 001 has NOT been executed, the imports are:

```python
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
| Server start  | `python app.py`                                 | Prints banner |
| API test      | `curl -X POST http://localhost:8765/api/repos/<id>/discard -H "Content-Type: application/json" -d "{}"` | 200 or relevant error |

## Scope

**In scope** (the only files you should modify):
- `git_scanner.py`
- `app.py`
- `models.py` (only if Plan 001 was NOT already executed and models are missing)

**Out of scope** (do NOT touch):
- `static/*` — frontend is Plan 004
- `ai_commit.py`, `notifier.py` — unrelated

## Git workflow

- Branch: `feat/phase2-discard-stash-backend`
- Commit style: `feat: add discard changes and stash creation endpoints`

## Steps

### Step 1: Verify or add Pydantic models

Check if `CreateStashRequest` and `DiscardRequest` exist in `models.py`.

```
python -c "from models import CreateStashRequest, DiscardRequest; print('OK')"
```

If this prints `OK`, skip to Step 2.

If it fails, add the following to `models.py` after the `StageRequest` class
(around line 103):

```python
class CreateStashRequest(BaseModel):
    message: Optional[str] = None
    include_untracked: bool = True

class DiscardRequest(BaseModel):
    files: Optional[List[str]] = None
```

**Verify**: `python -c "from models import CreateStashRequest, DiscardRequest; print('OK')"` → `OK`

### Step 2: Add `discard_file_changes` to `git_scanner.py`

Append after the last function in `git_scanner.py`:

```python
def discard_file_changes(repo_path: str, file_path: str) -> Tuple[bool, str]:
    """Discard working tree changes for a single file.

    For tracked (modified) files: uses 'git restore' to revert to HEAD state.
    For untracked files: deletes the file from disk.
    For deleted files that were tracked: restores from HEAD.
    """
    try:
        repo = Repo(repo_path)
        full_path = Path(repo_path) / file_path

        # Check if it's an untracked file
        if file_path in repo.untracked_files:
            if full_path.exists():
                if full_path.is_dir():
                    import shutil
                    shutil.rmtree(str(full_path))
                else:
                    full_path.unlink()
                return True, f"Removed untracked file '{file_path}'"
            return False, f"File '{file_path}' not found on disk"

        # For tracked files (modified or deleted): restore from HEAD
        try:
            repo.git.checkout('HEAD', '--', file_path)
            return True, f"Discarded changes in '{file_path}'"
        except git.GitCommandError:
            # Fallback: try git restore
            try:
                repo.git.restore(file_path)
                return True, f"Discarded changes in '{file_path}'"
            except git.GitCommandError as e2:
                return False, e2.stderr.strip() if e2.stderr else str(e2)

    except Exception as e:
        return False, str(e)
```

**Verify**: `python -c "from git_scanner import discard_file_changes; print('OK')"` → `OK`

### Step 3: Add `discard_all_changes` to `git_scanner.py`

Append after `discard_file_changes`:

```python
def discard_all_changes(repo_path: str) -> Tuple[bool, str]:
    """Discard ALL working tree changes: restore tracked files and remove untracked files.

    This is equivalent to:
      git checkout HEAD -- .
      git clean -fd
    """
    try:
        repo = Repo(repo_path)
        discarded = 0
        errors = []

        # Restore all tracked file modifications (modified, deleted)
        try:
            repo.git.checkout('HEAD', '--', '.')
            discarded += 1
        except git.GitCommandError:
            # May fail if no HEAD exists yet (empty repo)
            pass

        # Remove all untracked files and directories
        untracked = repo.untracked_files
        if untracked:
            for f in untracked:
                try:
                    full_path = Path(repo_path) / f
                    if full_path.exists():
                        if full_path.is_dir():
                            import shutil
                            shutil.rmtree(str(full_path))
                        else:
                            full_path.unlink()
                        discarded += 1
                except Exception as e:
                    errors.append(f"{f}: {str(e)}")

        # Also unstage any staged changes
        try:
            repo.git.reset('HEAD')
        except Exception:
            pass

        if errors:
            return True, f"Discarded changes with {len(errors)} warning(s): {'; '.join(errors[:3])}"
        return True, "All changes discarded"

    except Exception as e:
        return False, str(e)
```

**Verify**: `python -c "from git_scanner import discard_all_changes; print('OK')"` → `OK`

### Step 4: Add `create_stash` to `git_scanner.py`

Append after `discard_all_changes`:

```python
def create_stash(repo_path: str, message: Optional[str] = None, include_untracked: bool = True) -> Tuple[bool, str]:
    """Create a new stash entry with optional message.

    Stashes all working tree changes. If include_untracked is True, also
    stashes untracked files (equivalent to `git stash push -u`).
    """
    try:
        repo = Repo(repo_path)

        # Check if there's anything to stash
        if not repo.is_dirty(untracked_files=include_untracked):
            return False, "No changes to stash"

        args = ['push']
        if include_untracked:
            args.append('-u')
        if message:
            args.extend(['-m', message])

        repo.git.stash(*args)
        return True, f"Changes stashed{' as: ' + message if message else ''}"

    except git.GitCommandError as e:
        err = e.stderr.strip() if e.stderr else str(e)
        return False, err
    except Exception as e:
        return False, str(e)
```

**Verify**: `python -c "from git_scanner import create_stash; print('OK')"` → `OK`

### Step 5: Update `app.py` imports

Add the new functions to the `git_scanner` import block in `app.py`:

Find the existing import line from `git_scanner` and add
`discard_file_changes, discard_all_changes, create_stash` to the end.

Also add `CreateStashRequest, DiscardRequest` to the `models` import if
not already present.

**Verify**: `python -c "import app; print('OK')"` → `OK`

### Step 6: Add REST endpoints in `app.py`

Insert the following endpoints. The stash creation endpoint goes right after
the existing stash endpoints (after `stash_drop`). The discard endpoints
go in a new section.

**After the existing `stash_drop` endpoint**:

```python
@app.post("/api/repos/{repo_id}/stash")
async def stash_create(repo_id: str, req: CreateStashRequest):
    path = _find_repo_path(repo_id)
    ok, msg = create_stash(path, req.message, req.include_untracked)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"message": msg}
```

**New section — after stash, before staging endpoints**:

```python
# --- Discard Changes ---
@app.post("/api/repos/{repo_id}/discard")
async def discard_changes(repo_id: str, req: DiscardRequest):
    path = _find_repo_path(repo_id)

    if req.files and len(req.files) > 0:
        # Discard specific files
        results = []
        any_failed = False
        for f in req.files:
            ok, msg = discard_file_changes(path, f)
            results.append({"file": f, "ok": ok, "message": msg})
            if not ok:
                any_failed = True
        if any_failed and all(not r["ok"] for r in results):
            raise HTTPException(status_code=400, detail="Failed to discard all files")
        return {"message": f"Discarded {sum(1 for r in results if r['ok'])} file(s)", "results": results}
    else:
        # Discard all changes
        ok, msg = discard_all_changes(path)
        if not ok:
            raise HTTPException(status_code=400, detail=msg)
        return {"message": msg}
```

> **IMPORTANT**: The `POST /api/repos/{repo_id}/stash` route must be placed
> BEFORE the `POST /api/repos/{repo_id}/stash/apply` route, otherwise
> FastAPI may match the wrong route. Verify route order carefully.
>
> Actually, since "apply" is a sub-path, FastAPI's routing handles this
> correctly. But the stash creation endpoint MUST NOT conflict with
> `GET /api/repos/{repo_id}/stash` (listing). Since one is GET and the other
> is POST, they coexist on the same path without conflict.

**Verify**:
1. `python -c "import app; print('OK')"` → `OK`
2. Start server: `python app.py`
3. `curl http://localhost:8765/docs` → API docs should list the new endpoints

## Test plan

Manual verification:

1. **Create Stash (with message)**:
   - Make changes to a tracked repo.
   - `curl -X POST http://localhost:8765/api/repos/<id>/stash -H "Content-Type: application/json" -d '{"message": "WIP test", "include_untracked": true}'`
   - Expect 200 with `"Changes stashed as: WIP test"`.
   - `curl http://localhost:8765/api/repos/<id>/stash` → should list the new stash.

2. **Create Stash (no changes)**:
   - On a clean repo: `POST /stash` → expect 400 "No changes to stash".

3. **Discard Single File**:
   - Modify a tracked file.
   - `curl -X POST .../discard -d '{"files": ["<modified_file>"]}'`
   - Expect 200, file is reverted.

4. **Discard Untracked File**:
   - Create a new file in the repo.
   - `curl -X POST .../discard -d '{"files": ["<new_file>"]}'`
   - Expect 200, file is deleted from disk.

5. **Discard All Changes**:
   - Modify files and create untracked files.
   - `curl -X POST .../discard -d '{}'`
   - Expect 200, all changes reverted and untracked files removed.

## Done criteria

- [ ] `python -c "import app; print('OK')"` exits 0
- [ ] `POST /api/repos/{id}/stash` with message creates a stash
- [ ] `POST /api/repos/{id}/stash` on clean repo returns 400
- [ ] `POST /api/repos/{id}/discard` with `files: [...]` discards specific files
- [ ] `POST /api/repos/{id}/discard` with `files: null` discards all changes
- [ ] Untracked files are deleted from disk when discarded
- [ ] Modified tracked files are reverted to HEAD when discarded
- [ ] No files outside in-scope list are modified (`git status`)

## STOP conditions

Stop and report back (do not improvise) if:

- `git restore` or `git checkout HEAD -- <file>` is not available in the
  installed git version (requires git >= 2.23 for `restore`).
- `repo.git.stash('push', '-u', '-m', msg)` fails with an unexpected error.
- Discarding files causes data loss beyond the intended scope (e.g.,
  affecting `.gitignore`d files like `.env`).
- A step's verification fails twice after a reasonable fix attempt.

## Maintenance notes

- **Safety**: `discard_all_changes` runs `git checkout HEAD -- .` (tracked)
  + manual file deletion (untracked). It does NOT use `git clean -fd`
  directly because that command could delete files matching complex
  `.gitignore` rules unexpectedly. Manual deletion of `repo.untracked_files`
  is safer because GitPython's `untracked_files` property already respects
  `.gitignore`.
- **Route ordering**: `POST /api/repos/{id}/stash` (create) and
  `GET /api/repos/{id}/stash` (list) share the same path with different
  HTTP methods. FastAPI handles this correctly.
- **Future**: A "selective stash" feature (stash only specific files) would
  require `git stash push -- <file1> <file2>`. The `CreateStashRequest`
  model could be extended with an optional `files` list.
