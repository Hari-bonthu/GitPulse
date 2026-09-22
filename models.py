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

class InitRepoRequest(BaseModel):
    path: str
    default_branch: str = "main"
    create_gitignore: bool = True

class PublishRepoRequest(BaseModel):
    remote_url: str
    remote_name: str = "origin"

class CommitRequest(BaseModel):
    message: str
    files: Optional[List[str]] = None

class StageRequest(BaseModel):
    files: List[str]

class GenerateCommitMessageRequest(BaseModel):
    repo_id: str
    files: Optional[List[str]] = None
    style: Optional[str] = "conventional"  # "conventional", "concise", "detailed"

class GenerateCommitMessageResponse(BaseModel):
    message: str
    provider: str

class SecretLeak(BaseModel):
    file: str
    line_snippet: str
    rule: str
    risk: str

class ReviewChangesRequest(BaseModel):
    repo_id: str
    files: Optional[List[str]] = None

class ReviewChangesResponse(BaseModel):
    summary: str
    risk_level: str  # "LOW", "MEDIUM", "HIGH"
    findings: List[str]
    leaks: List[SecretLeak]
    debug_artifacts: List[str]

class GeneratePRRequest(BaseModel):
    repo_id: str

class GeneratePRResponse(BaseModel):
    title: str
    body: str
    unpushed_count: int
    commits: List[CommitEntry]

class BatchFetchResult(BaseModel):
    id: str
    name: str
    ok: bool
    message: str

class BatchFetchResponse(BaseModel):
    total: int
    success_count: int
    results: List[BatchFetchResult]

class Settings(BaseModel):
    staleness_threshold_days: int = 3
    auto_refresh_seconds: int = 60
    notification_quiet_start: Optional[str] = "22:00"
    notification_quiet_end: Optional[str] = "08:00"
    ai_provider: str = "gemini"
    gemini_api_key: Optional[str] = ""
    openai_api_key: Optional[str] = ""
    theme: str = "system"

class RepoConfig(BaseModel):
    id: str
    path: str

class AppConfig(BaseModel):
    repos: List[RepoConfig]
    settings: Settings
