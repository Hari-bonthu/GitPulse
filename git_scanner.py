import git
from git import Repo, InvalidGitRepositoryError, NoSuchPathError
from pathlib import Path
from models import *
import os
import re
from datetime import datetime, timezone
from typing import Optional, List, Tuple

def validate_git_repo(path: str) -> Tuple[bool, str]:
    try:
        Repo(path)
        return True, ""
    except InvalidGitRepositoryError:
        return False, "Not a valid git repository"
    except NoSuchPathError:
        return False, "Path does not exist"
    except Exception as e:
        return False, str(e)

def get_repo_id(path: str) -> str:
    path_obj = Path(path)
    base = path_obj.name
    parent = path_obj.parent.name
    safe_name = re.sub(r'[^a-zA-Z0-9_-]', '_', f"{parent}_{base}")
    return safe_name

def _get_relative_time(dt: datetime) -> str:
    now = datetime.now(timezone.utc)
    diff = now - dt
    if diff.days > 365:
        return f"{diff.days // 365} years ago"
    if diff.days > 30:
        return f"{diff.days // 30} months ago"
    if diff.days > 0:
        return f"{diff.days} days ago"
    if diff.seconds > 3600:
        return f"{diff.seconds // 3600} hours ago"
    if diff.seconds > 60:
        return f"{diff.seconds // 60} minutes ago"
    return "just now"

def get_changed_files(repo: Repo) -> List[ChangedFile]:
    changed = []
    try:
        for file in repo.untracked_files:
            changed.append(ChangedFile(path=file, status=FileStatus.UNTRACKED))
            
        try:
            head_commit = repo.head.commit
            diff_index = head_commit.diff(None)
        except ValueError:
            diff_index = []
            
        for d in diff_index:
            status = FileStatus.MODIFIED
            if d.change_type == 'A': status = FileStatus.ADDED
            elif d.change_type == 'D': status = FileStatus.DELETED
            elif d.change_type == 'R': status = FileStatus.RENAMED
            elif d.change_type == 'C': status = FileStatus.COPIED
            
            changed.append(ChangedFile(path=d.b_path or d.a_path, status=status, old_path=d.a_path if status == FileStatus.RENAMED else None))
            
    except Exception:
        pass
        
    return changed

def build_file_tree(changed_files: List[ChangedFile]) -> List[TreeNode]:
    root: dict = {}
    for cf in changed_files:
        parts = cf.path.split('/')
        current = root
        for i, part in enumerate(parts):
            if i == len(parts) - 1:
                current[part] = {'__type__': 'file', 'status': cf.status, 'path': cf.path}
            else:
                if part not in current:
                    current[part] = {}
                current = current[part]
                
    def _dict_to_tree(d: dict, current_path: str) -> List[TreeNode]:
        nodes = []
        for k, v in d.items():
            if k == '__type__': continue
            node_path = f"{current_path}/{k}" if current_path else k
            if isinstance(v, dict) and v.get('__type__') == 'file':
                nodes.append(TreeNode(name=k, path=v['path'], is_dir=False, status=v['status']))
            else:
                children = _dict_to_tree(v, node_path)
                nodes.append(TreeNode(name=k, path=node_path, is_dir=True, children=children))
        return nodes
        
    return _dict_to_tree(root, "")

def get_branch_info(repo: Repo) -> BranchInfo:
    try:
        branch_name = repo.active_branch.name
    except (TypeError, ValueError):
        try:
            branch_name = repo.git.symbolic_ref('--short', 'HEAD')
        except Exception:
            branch_name = "main (initial)"
    except Exception:
        branch_name = "HEAD (detached)"
    
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

def get_commit_log(repo: Repo, count: int = 15) -> List[CommitEntry]:
    commits = []
    try:
        for c in repo.iter_commits(max_count=count):
            dt = datetime.fromtimestamp(c.committed_date, tz=timezone.utc)
            commits.append(CommitEntry(
                hash=c.hexsha[:7],
                full_hash=c.hexsha,
                message=c.message.strip().split('\n')[0],
                author=c.author.name,
                timestamp=_get_relative_time(dt)
            ))
    except Exception:
        pass
    return commits

def get_stash_list(repo: Repo) -> List[StashEntry]:
    stashes = []
    try:
        stash_output = repo.git.stash('list')
        if not stash_output: return stashes
        for line in stash_output.strip().split('\n'):
            match = re.match(r'stash@\{(\d+)\}: (?:WIP on |On )([^:]+): (.*)', line)
            if match:
                index, branch, msg = match.groups()
                stashes.append(StashEntry(index=int(index), message=msg, timestamp="Unknown", branch=branch))
    except Exception:
        pass
    return stashes

def get_diff_for_file(repo: Repo, file_path: str) -> str:
    try:
        diff = repo.git.diff('--', file_path)
        if not diff:
            diff = repo.git.diff('--cached', '--', file_path)
        return diff
    except Exception:
        return ""

def _compute_health(repo: Repo, branch: BranchInfo, changed_files: list, staleness_days: int) -> RepoHealth:
    if changed_files:
        return RepoHealth.DIRTY
    if branch.ahead > 0:
        return RepoHealth.UNPUSHED
    if branch.behind > 0:
        return RepoHealth.BEHIND
    try:
        last_commit = next(repo.iter_commits(max_count=1))
        dt = datetime.fromtimestamp(last_commit.committed_date, tz=timezone.utc)
        if (datetime.now(timezone.utc) - dt).days >= staleness_days:
            return RepoHealth.STALE
    except StopIteration:
        pass
    return RepoHealth.CLEAN

def get_repo_status(path: str) -> RepoStatus:
    repo = Repo(path)
    changed_files = get_changed_files(repo)
    branch = get_branch_info(repo)
    health = _compute_health(repo, branch, changed_files, 3)
    
    untracked_count = sum(1 for c in changed_files if c.status == FileStatus.UNTRACKED)
    stashes = get_stash_list(repo)
    
    last_time = None
    last_msg = None
    try:
        last_commit = next(repo.iter_commits(max_count=1))
        dt = datetime.fromtimestamp(last_commit.committed_date, tz=timezone.utc)
        last_time = _get_relative_time(dt)
        last_msg = last_commit.message.strip().split('\n')[0]
    except Exception:
        pass

    return RepoStatus(
        id=get_repo_id(path),
        name=Path(path).name,
        path=path,
        branch=branch,
        health=health,
        changed_files=changed_files,
        untracked_count=untracked_count,
        stash_count=len(stashes),
        last_commit_time=last_time,
        last_commit_message=last_msg
    )

def get_repo_summary(path: str, staleness_days: int = 3) -> RepoSummary:
    repo = Repo(path)
    changed_files = get_changed_files(repo)
    branch = get_branch_info(repo)
    health = _compute_health(repo, branch, changed_files, staleness_days)
    
    untracked_count = sum(1 for c in changed_files if c.status == FileStatus.UNTRACKED)
    stashes = get_stash_list(repo)
    
    last_time = None
    last_msg = None
    try:
        last_commit = next(repo.iter_commits(max_count=1))
        dt = datetime.fromtimestamp(last_commit.committed_date, tz=timezone.utc)
        last_time = _get_relative_time(dt)
        last_msg = last_commit.message.strip().split('\n')[0]
    except Exception:
        pass

    return RepoSummary(
        id=get_repo_id(path),
        name=Path(path).name,
        path=path,
        branch_name=branch.name,
        health=health,
        changed_count=len(changed_files),
        untracked_count=untracked_count,
        unpushed_count=branch.ahead,
        stash_count=len(stashes),
        last_commit_time=last_time,
        last_commit_message=last_msg
    )

def init_repo(path: str, default_branch: str = "main", create_gitignore: bool = True) -> Tuple[bool, str]:
    try:
        p = Path(path)
        if not p.exists():
            p.mkdir(parents=True, exist_ok=True)
        
        if (p / ".git").exists():
            return False, "Directory is already a Git repository"
        
        repo = Repo.init(str(p), initial_branch=default_branch)
        
        if create_gitignore and not (p / ".gitignore").exists():
            default_ignore = (
                "# Environment & Secrets\n.env\n*.env\nconfig.json\n\n"
                "# Python\n__pycache__/\n*.py[cod]\nvenv/\n.venv/\n\n"
                "# Node\nnode_modules/\n\n"
                "# IDE\n.vscode/\n.idea/\n*.swp\n\n"
                "# OS\n.DS_Store\nThumbs.db\n"
            )
            with open(p / ".gitignore", "w", encoding="utf-8") as f:
                f.write(default_ignore)
        
        repo.close()
        return True, f"Initialized empty Git repository on branch '{default_branch}'"
    except Exception as e:
        return False, str(e)

def stage_files(repo_path: str, files: List[str]) -> bool:
    try:
        repo = Repo(repo_path)
        if not files:
            return True

        ignored = set()
        try:
            ignored = set(repo.ignored(*files))
        except Exception:
            pass

        to_add = [f for f in files if f not in ignored]
        if to_add:
            repo.git.add(*to_add)

        # For any ignored file that was already tracked in the index, update it
        if ignored:
            for f in ignored:
                try:
                    if f in repo.index.entries:
                        repo.git.add('-f', f)
                except Exception:
                    pass

        return True
    except Exception:
        return False

def unstage_files(repo_path: str, files: List[str]) -> bool:
    try:
        repo = Repo(repo_path)
        repo.git.restore('--staged', *files)
        return True
    except Exception:
        return False

def commit_changes(repo_path: str, message: str, files: Optional[List[str]] = None) -> Tuple[bool, str]:
    try:
        repo = Repo(repo_path)
        if files:
            ignored = set()
            try:
                ignored = set(repo.ignored(*files))
            except Exception:
                pass

            to_add = [f for f in files if f not in ignored]
            if to_add:
                repo.git.add(*to_add)

            # For any ignored file that was already tracked in index, allow adding with force
            if ignored:
                for ig in ignored:
                    try:
                        if ig in repo.index.entries:
                            repo.git.add('-f', ig)
                    except Exception:
                        pass
        else:
            try:
                has_staged = bool(repo.index.diff('HEAD'))
            except Exception:
                has_staged = bool(repo.index.entries)
            if not has_staged:
                repo.git.add(A=True)
        
        try:
            has_head = True
            _ = repo.head.commit
        except Exception:
            has_head = False

        if has_head:
            if not repo.index.diff('HEAD'):
                return False, "Nothing staged to commit"
        else:
            if not repo.index.entries:
                return False, "Nothing staged to commit"
            
        commit = repo.index.commit(message)
        return True, commit.hexsha[:7]
    except git.GitCommandError as e:
        err = e.stderr.strip() if e.stderr else str(e)
        if "The following paths are ignored" in err:
            err = err.split("hint:")[0].strip()
        return False, err
    except Exception as e:
        return False, str(e)

def push_changes(repo_path: str) -> Tuple[bool, str]:
    try:
        repo = Repo(repo_path)
        if repo.active_branch.tracking_branch() is None:
            return False, "No upstream branch configured"
        push_info = repo.remotes.origin.push()
        if push_info and push_info[0].flags & git.remote.PushInfo.ERROR:
            return False, push_info[0].summary
        return True, "Pushed successfully"
    except Exception as e:
        return False, str(e)

def publish_repo_to_remote(repo_path: str, remote_url: str, remote_name: str = "origin") -> Tuple[bool, str]:
    try:
        repo = Repo(repo_path)
        url = remote_url.strip()
        if not url:
            return False, "Remote URL cannot be empty"

        # Check if remote already exists
        existing_names = [r.name for r in repo.remotes]
        if remote_name in existing_names:
            remote = repo.remote(remote_name)
            remote.set_url(url)
        else:
            remote = repo.create_remote(remote_name, url)

        # Active branch
        try:
            branch_name = repo.active_branch.name
        except Exception:
            branch_name = repo.git.symbolic_ref('--short', 'HEAD')

        # Push with -u
        repo.git.push('-u', remote_name, branch_name)
        return True, f"Successfully published to {url} ({remote_name}/{branch_name})"
    except git.GitCommandError as e:
        err = e.stderr.strip() if e.stderr else str(e)
        return False, err
    except Exception as e:
        return False, str(e)

def apply_stash(repo_path: str, index: int = 0) -> Tuple[bool, str]:
    try:
        repo = Repo(repo_path)
        repo.git.stash('apply', f'stash@{{{index}}}')
        return True, "Stash applied"
    except Exception as e:
        return False, str(e)

def pop_stash(repo_path: str, index: int = 0) -> Tuple[bool, str]:
    try:
        repo = Repo(repo_path)
        repo.git.stash('pop', f'stash@{{{index}}}')
        return True, "Stash popped"
    except Exception as e:
        return False, str(e)

def drop_stash(repo_path: str, index: int) -> Tuple[bool, str]:
    try:
        repo = Repo(repo_path)
        repo.git.stash('drop', f'stash@{{{index}}}')
        return True, "Stash dropped"
    except Exception as e:
        return False, str(e)

def check_repo_access(repo_path: str) -> Tuple[bool, str]:
    try:
        if not os.access(repo_path, os.R_OK | os.W_OK):
            return False, "No read/write access to repository path"
        repo = Repo(repo_path)
        return True, "Access ok"
    except Exception as e:
        return False, str(e)


def list_branches(repo_path: str) -> List[BranchItem]:
    """List all local and remote branches with active HEAD indicator."""
    try:
        repo = Repo(repo_path)
        branches = []

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
                branches.append(BranchItem(
                    name=ref.name,  # e.g. "origin/main"
                    is_active=False,
                    is_remote=True,
                    tracking=None,
                ))

        return branches
    except Exception:
        return []


def checkout_branch(repo_path: str, branch_name: str, create: bool = False) -> Tuple[bool, str]:
    """Switch to an existing branch or create a new one."""
    try:
        repo = Repo(repo_path)

        if create:
            if branch_name in [h.name for h in repo.heads]:
                return False, f"Branch '{branch_name}' already exists"
            repo.git.checkout('-b', branch_name)
            return True, f"Created and switched to branch '{branch_name}'"

        # Check if it's a remote branch reference (e.g. origin/feature-x)
        is_remote_ref = '/' in branch_name and branch_name not in [h.name for h in repo.heads]
        if is_remote_ref:
            parts = branch_name.split('/', 1)
            local_name = parts[1] if len(parts) == 2 else branch_name
            if local_name in [h.name for h in repo.heads]:
                repo.git.checkout(local_name)
                return True, f"Switched to existing local branch '{local_name}'"
            repo.git.checkout('-b', local_name, '--track', branch_name)
            return True, f"Created local branch '{local_name}' tracking '{branch_name}'"

        if branch_name not in [h.name for h in repo.heads]:
            return False, f"Branch '{branch_name}' not found"

        repo.git.checkout(branch_name)
        return True, f"Switched to branch '{branch_name}'"

    except git.GitCommandError as e:
        err = e.stderr.strip() if e.stderr else str(e)
        return False, err
    except Exception as e:
        return False, str(e)


def fetch_remote(repo_path: str, remote_name: str = "origin") -> Tuple[bool, str]:
    """Fetch latest refs from the specified remote."""
    try:
        repo = Repo(repo_path)
        if not repo.remotes:
            return False, "No remote configured"

        remote_names = [r.name for r in repo.remotes]
        if remote_name not in remote_names:
            remote_name = remote_names[0]

        repo.git.fetch(remote_name)
        return True, f"Fetched from '{remote_name}'"
    except git.GitCommandError as e:
        err = e.stderr.strip() if e.stderr else str(e)
        return False, err
    except Exception as e:
        return False, str(e)


def pull_changes(repo_path: str, rebase: bool = False) -> Tuple[bool, str]:
    """Pull upstream changes into the current branch."""
    try:
        repo = Repo(repo_path)

        try:
            tracking = repo.active_branch.tracking_branch()
        except (TypeError, ValueError):
            return False, "Cannot pull: HEAD is detached"

        if not tracking:
            return False, "No upstream tracking branch configured. Push first to set upstream."

        args = ['--rebase'] if rebase else []
        result = repo.git.pull(*args)

        if repo.index.unmerged_blobs():
            return False, "Pull completed with merge conflicts. Resolve conflicts before committing."

        summary = result.strip() if result else "Already up to date"
        if len(summary) > 200:
            summary = summary[:200] + "..."
        return True, summary

    except git.GitCommandError as e:
        err = e.stderr.strip() if e.stderr else str(e)
        if "CONFLICT" in str(e) or "Merge conflict" in str(e):
            return False, "Merge conflict detected. Resolve conflicts manually before continuing."
        if "Could not resolve host" in err:
            return False, "Network error: could not reach remote. Check your internet connection."
        return False, err
    except Exception as e:
        return False, str(e)


def discard_file_changes(repo_path: str, file_path: str) -> Tuple[bool, str]:
    """Discard working tree changes for a single file."""
    try:
        repo = Repo(repo_path)
        full_path = Path(repo_path) / file_path

        # If untracked
        if file_path in repo.untracked_files:
            if full_path.exists():
                if full_path.is_dir():
                    import shutil
                    shutil.rmtree(str(full_path))
                else:
                    full_path.unlink()
                return True, f"Removed untracked file '{file_path}'"
            return False, f"File '{file_path}' not found on disk"

        # If tracked, unstage first if staged, then checkout from HEAD
        try:
            repo.git.restore('--staged', file_path)
        except Exception:
            pass

        try:
            repo.git.checkout('HEAD', '--', file_path)
            return True, f"Discarded changes in '{file_path}'"
        except git.GitCommandError:
            try:
                repo.git.restore(file_path)
                return True, f"Discarded changes in '{file_path}'"
            except git.GitCommandError as e2:
                return False, e2.stderr.strip() if e2.stderr else str(e2)

    except Exception as e:
        return False, str(e)


def discard_all_changes(repo_path: str) -> Tuple[bool, str]:
    """Discard ALL working tree changes: restore tracked files and remove untracked files."""
    try:
        repo = Repo(repo_path)
        errors = []

        # Reset index
        try:
            repo.git.reset('HEAD')
        except Exception:
            pass

        # Restore tracked modifications
        try:
            repo.git.checkout('HEAD', '--', '.')
        except git.GitCommandError:
            pass

        # Remove untracked files and directories
        untracked = list(repo.untracked_files)
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
                except Exception as e:
                    errors.append(f"{f}: {str(e)}")

        if errors:
            return True, f"Discarded changes with {len(errors)} warning(s): {'; '.join(errors[:3])}"
        return True, "All changes discarded"

    except Exception as e:
        return False, str(e)


def create_stash(repo_path: str, message: Optional[str] = None, include_untracked: bool = True) -> Tuple[bool, str]:
    """Create a new stash entry with optional message."""
    try:
        repo = Repo(repo_path)

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
