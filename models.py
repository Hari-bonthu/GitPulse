from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum
from datetime import datetime

class FileStatus(str, Enum):
    MODIFIED = "MODIFIED"
    ADDED = "ADDED"
    DELETED = "DELETED"
    RENAMED = "RENAMED"
    UNTRACKED = "UNTRACKED"
    COPIED = "COPIED"

class RepoHealth(str, Enum):
    CLEAN = "CLEAN"
    DIRTY = "DIRTY"
    UNPUSHED = "UNPUSHED"
    BEHIND = "BEHIND"
    STALE = "STALE"

class ChangedFile(BaseModel):
    path: str
    status: FileStatus
    old_path: Optional[str] = None

class TreeNode(BaseModel):
    name: str
    path: str
    is_dir: bool
    status: Optional[FileStatus] = None
    children: List['TreeNode'] = []

TreeNode.model_rebuild()

class StashEntry(BaseModel):
    index: int
    message: str
    timestamp: str
    branch: str

class CommitEntry(BaseModel):
    hash: str
    message: str
    author: str
    timestamp: str
    full_hash: str

class BranchInfo(BaseModel):
    name: str
    remote_name: Optional[str] = None
    ahead: int = 0
    behind: int = 0

class RepoStatus(BaseModel):
    id: str
    name: str
    path: str
    branch: BranchInfo
    health: RepoHealth
    changed_files: List[ChangedFile]
    untracked_count: int
    stash_count: int
    last_commit_time: Optional[str] = None
    last_commit_message: Optional[str] = None

class RepoSummary(BaseModel):
    id: str
    name: str
    path: str
    branch_name: str
    health: RepoHealth
    changed_count: int
    untracked_count: int
    unpushed_count: int
    stash_count: int
    last_commit_time: Optional[str] = None
    last_commit_message: Optional[str] = None

class DashboardSummary(BaseModel):
    total_repos: int
    repos_needing_attention: int
    repos_with_unpushed: int
    stale_repos: int
    repo_summaries: List[RepoSummary]

class AddRepoRequest(BaseModel):
    path: str

class CommitRequest(BaseModel):
    message: str
    files: Optional[List[str]] = None

class StageRequest(BaseModel):
    files: List[str]

class GenerateCommitMessageRequest(BaseModel):
    repo_id: str

class GenerateCommitMessageResponse(BaseModel):
    message: str
    provider: str

class Settings(BaseModel):
    staleness_threshold_days: int = 3
    auto_refresh_seconds: int = 60
    notification_quiet_start: Optional[str] = "22:00"
    notification_quiet_end: Optional[str] = "08:00"
    ai_provider: str = "gemini"
    theme: str = "system"

class RepoConfig(BaseModel):
    id: str
    path: str

class AppConfig(BaseModel):
    repos: List[RepoConfig]
    settings: Settings
