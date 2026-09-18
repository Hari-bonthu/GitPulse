<div align="center">

# GitPulse

**Multi-Repository Git Tracking Dashboard, Staging Workspace & AI Commit Assistant**

A unified, local-first command center for developers managing multiple Git repositories concurrently. Inspect uncommitted changes, track unpushed branches, manage stashes, and generate semantic commit messages from a single interface.

[![Python](https://img.shields.io/badge/python-3.10+-3776ab?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![GitPython](https://img.shields.io/badge/GitPython-3.1-f05032?style=flat-square&logo=git&logoColor=white)](https://gitpython.readthedocs.io/)
[![Google Gemini](https://img.shields.io/badge/Gemini-2.0_Flash-4285f4?style=flat-square&logo=google&logoColor=white)](https://aistudio.google.com/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue?style=flat-square)](LICENSE)

<br />

<!-- Demo / Preview Placeholder -->
<p align="center">
  <img src="https://raw.githubusercontent.com/username/gitpulse/main/static/preview.png" alt="GitPulse Dashboard Preview" width="860" style="max-width: 100%; border-radius: 8px; box-shadow: 0 4px 20px rgba(0,0,0,0.15);" />
</p>

[Key Features](#key-features) • [Architecture](#architecture) • [Quickstart](#quickstart) • [Configuration](#configuration) • [REST API Reference](#rest-api-reference) • [Keyboard Shortcuts](#keyboard-shortcuts) • [Design System](#design-system--interaction-standards) • [Security & Privacy](#security--local-first-guarantee) • [Troubleshooting](#troubleshooting) • [Contributing](#contributing) • [License](#license)

</div>

---

## Overview

When actively developing across multiple client projects, microservices, or interdependent packages, tracking Git state across every repository quickly becomes friction-heavy:

- **Forgotten Working Copies:** Unstaged modifications and untracked files sit unnoticed for days across background directories.
- **Out-of-Sync Upstreams:** Commits are completed locally on feature branches but left unpushed, resulting in outdated pull requests and deployment delays.
- **Orphaned Stashes:** Experimental branches and stashed changes are easily lost without a visual audit trail.
- **Context-Switching Drag:** Cycling through multiple terminal windows or opening distinct IDE instances simply to inspect `git status` creates cognitive fatigue.

**GitPulse provides a consolidated, browser-based overview of your entire workspace.** It monitors your local repositories in real-time, displays collapsible file trees with selective staging checkboxes, renders syntax-colored diffs, and synthesizes conventional commit messages using Google Gemini or OpenAI with zero external server dependencies.

---

## Key Features

- **Multi-Repository Health Radar:** Automatically classifies repository health states (`CLEAN`, `DIRTY`, `UNPUSHED`, `BEHIND`, `STALE`) based on uncommitted changes, untracked files, and upstream commit differentials.
- **IDE-Style Collapsible File Tree:** Hierarchical tree breakdown of modified, added, deleted, renamed, and untracked files with granular staging checkboxes.
- **Interactive Unified Diff Viewer:** Inspect file additions and deletions line-by-line with syntax gutters and added/removed line metrics before committing.
- **Context-Aware AI Commit Generator:** Analyzes staged diffs and untracked file signatures to produce structured conventional commit messages (`feat:`, `fix:`, `refactor:`) via Google Gemini or OpenAI.
- **Heuristic Offline Fallback:** If API credentials are unavailable or the network is offline, a built-in static analyzer generates compliant conventional commits directly from diff headers.
- **Atomic Commit & Push Operations:** Execute local commits independently or trigger unified commit-and-push transactions directly from the interface.
- **Full Stash Lifecycle Management:** Review stash indices, messages, creation dates, and branch origins with one-click `apply`, `pop`, and `drop` actions.
- **Desktop Watchdog Alerts:** Background notification scheduler powered by `plyer` delivers native desktop toasts when repositories require attention, respecting configurable quiet hours.
- **Tailored Micro-Interactions:** Implemented following Emil Kowalski motion principles (`cubic-bezier(0.23, 1, 0.32, 1)`) with physical button-press scaling and stacked Sonner-style toast notifications.
- **Strict Visual Discipline:** 100% vector SVG iconography via Lucide Icons with zero low-fidelity emojis.

---

## Architecture

```text
+-----------------------------------------------------------------------------+
|                            Browser UI (SPA)                                 |
|            HTML5 + Modern JavaScript (ES6+) + Tailwind CSS + Lucide          |
|                                                                             |
|   +-------------------+  +--------------------+  +----------------------+   |
|   | Dashboard Overview|  | File Tree & Diff   |  | Stash Management &   |   |
|   | Health Badges     |  | Staging Checkboxes |  | Settings Modal       |   |
|   +---------+---------+  +---------+----------+  +----------+-----------+   |
|             |                      |                        |               |
|             +----------------------+------------------------+               |
|                                    | HTTP / JSON REST API                   |
+------------------------------------+----------------------------------------+
                                     |
                                     v
+-----------------------------------------------------------------------------+
|                           FastAPI Backend Service                           |
|                                                                             |
|   +---------------------+  +--------------------+  +--------------------+   |
|   | app.py (REST API)   |  | git_scanner.py     |  | ai_commit.py       |   |
|   | Routing, Lifespan,  |  | GitPython Engine,  |  | Gemini 2.0 Flash / |   |
|   | Static File Mount   |  | Tree, Diff, Stash  |  | OpenAI / Offline   |   |
|   +----------+----------+  +---------+----------+  +---------+----------+   |
|              |                       |                       |              |
|   +----------+----------+  +---------+----------+            |              |
|   | notifier.py         |  | models.py          |            |              |
|   | Desktop Toasts &    |  | Pydantic v2 Schemas|            |              |
|   | Background Watchdog |  | & Type Validation  |            |              |
|   +---------------------+  +--------------------+            |              |
+--------------------------------------+-----------------------+--------------+
                                       |                       |
                     +-----------------+                       | HTTPS
                     v                                         v
        +-------------------------+               +-------------------------+
        | Local Git Repositories  |               | AI Provider Gateways    |
        | (.git File System)      |               | Google AI / OpenAI APIs |
        +-------------------------+               +-------------------------+
```

---

## Tech Stack

| Domain | Technology | Description |
|---|---|---|
| **Backend Framework** | [FastAPI](https://fastapi.tiangolo.com/) | High-performance Python ASGI web framework |
| **ASGI Server** | [Uvicorn](https://www.uvicorn.org/) | Lightning-fast async web server implementation |
| **Git Automation** | [GitPython](https://gitpython.readthedocs.io/) | Native Git repository interaction and plumbing |
| **Data Contracts** | [Pydantic v2](https://docs.pydantic.dev/) | Strict data parsing and model validation |
| **AI Synthesis** | [Google Gemini](https://ai.google.dev/) / [OpenAI](https://platform.openai.com/) | LLM diff analysis for semantic commit generation |
| **Desktop Notifications** | [Plyer](https://plyer.readthedocs.io/) | Platform-independent desktop notification wrapper |
| **Frontend Runtime** | Vanilla Modern JavaScript (ES6+) | Dependency-free, lightweight client architecture |
| **Design & Styling** | Tailwind CSS + Lucide Icons | Clean typography, dark/light themes, and crisp SVG icons |

---

## Quickstart

Follow these steps to set up and run GitPulse locally:

### 1. Clone the Repository
```bash
git clone https://github.com/username/gitpulse.git
cd gitpulse
```

### 2. Create Virtual Environment & Install Dependencies
```bash
# On Linux / macOS:
python3 -m venv venv
source venv/bin/activate

# On Windows:
python -m venv venv
.\venv\Scripts\activate

# Install requirements
pip install -r requirements.txt
```

### 3. Configure Environment (Optional)
To enable AI commit message generation, copy the sample configuration and supply an API key:
```bash
# On Linux / macOS:
cp .env.example .env

# On Windows:
copy .env.example .env
```

Edit `.env`:
```ini
AI_PROVIDER=gemini
GEMINI_API_KEY=your_gemini_api_key_here
# OPENAI_API_KEY=your_openai_api_key_here
```

> [!NOTE]
> GitPulse runs fully offline without an API key. If no key is set, the offline conventional commit engine automatically analyzes changes locally.

### 4. Launch GitPulse
```bash
python app.py
```
*(On Windows systems, you can also double-click `run_gitpulse.bat`)*

Open your browser and navigate to:
```text
http://127.0.0.1:8765
```

Interactive OpenAPI documentation is available at:
```text
http://127.0.0.1:8765/docs
```

---

## Configuration

GitPulse automatically creates your local `config.json` on first launch from `config.example.json`. Your personal `config.json` is **gitignored by default** so your local repository paths are kept private and never committed to version control:

```json
{
  "repos": [
    {
      "id": "sample_repo",
      "path": "/path/to/local/git/repository"
    }
  ],
  "settings": {
    "staleness_threshold_days": 3,
    "auto_refresh_seconds": 60,
    "notification_quiet_start": "22:00",
    "notification_quiet_end": "08:00",
    "ai_provider": "gemini",
    "theme": "system"
  }
}
```

### Configuration Options

| Option | Type | Default | Description |
|---|---|---|---|
| `staleness_threshold_days` | integer | `3` | Number of days since the last commit before a repository is flagged as `STALE`. |
| `auto_refresh_seconds` | integer | `60` | Polling frequency in seconds for background status audits. |
| `notification_quiet_start` | string | `"22:00"` | 24-hour timestamp indicating when desktop notifications should be muted. |
| `notification_quiet_end` | string | `"08:00"` | 24-hour timestamp indicating when notifications may resume. |
| `ai_provider` | string | `"gemini"` | Default LLM provider for commit generation (`"gemini"` or `"openai"`). |
| `theme` | string | `"system"` | UI color scheme preference (`"system"`, `"dark"`, or `"light"`). |

---

## REST API Reference

GitPulse provides an OpenAPI-compliant REST interface.

### Dashboard & Repository Overview

| Method | Endpoint | Status | Description |
|---|---|---|---|
| `GET` | `/api/dashboard` | `200` | Fetch aggregated counts and repository summary list. |
| `GET` | `/api/repos` | `200` | Retrieve summaries of all tracked repositories. |
| `POST` | `/api/repos` | `200 / 400` | Track a new local repository path. |
| `DELETE` | `/api/repos/{repo_id}` | `200 / 404` | Untrack a repository (does not delete local disk files). |

#### Track Repository Example
```bash
curl -X POST http://127.0.0.1:8765/api/repos \
  -H "Content-Type: application/json" \
  -d '{"path": "/absolute/path/to/my-repo"}'
```

---

### File Inspection & Git Operations

| Method | Endpoint | Status | Description |
|---|---|---|---|
| `GET` | `/api/repos/{repo_id}/status` | `200` | Full repository status, branch info, and changed file listing. |
| `GET` | `/api/repos/{repo_id}/tree` | `200` | Hierarchical JSON tree structure of all modified/untracked files. |
| `GET` | `/api/repos/{repo_id}/diff?file={path}` | `200` | Unified Git diff text for a specified relative file path. |
| `GET` | `/api/repos/{repo_id}/log?count={n}` | `200` | Retrieve the `n` most recent commit log entries. |
| `POST` | `/api/repos/{repo_id}/stage` | `200` | Stage a list of specified files. |
| `POST` | `/api/repos/{repo_id}/unstage` | `200` | Unstage a list of specified files. |
| `POST` | `/api/repos/{repo_id}/commit` | `200 / 400` | Commit staged changes with provided message. |
| `POST` | `/api/repos/{repo_id}/push` | `200 / 400` | Push committed changes to the tracking upstream branch. |
| `POST` | `/api/repos/{repo_id}/commit-push` | `200 / 400` | Atomic single-action commit and push. |

#### Stage & Commit Payload
```json
{
  "message": "feat(scanner): add recursive submodule tree detection",
  "files": [
    "git_scanner.py",
    "models.py"
  ]
}
```

---

### Stash Operations

| Method | Endpoint | Status | Description |
|---|---|---|---|
| `GET` | `/api/repos/{repo_id}/stash` | `200` | List all stashes with index, message, branch, and timestamp. |
| `POST` | `/api/repos/{repo_id}/stash/apply?index={i}` | `200 / 400` | Apply stash entry `i` without removing it from the stack. |
| `POST` | `/api/repos/{repo_id}/stash/pop?index={i}` | `200 / 400` | Apply and remove stash entry `i`. |
| `DELETE` | `/api/repos/{repo_id}/stash/{i}` | `200 / 400` | Drop stash entry `i`. |

---

### AI Commit Generation

| Method | Endpoint | Status | Description |
|---|---|---|---|
| `POST` | `/api/ai/generate-commit` | `200` | Analyze current diff and generate a semantic commit message. |

#### Request Payload
```json
{
  "repo_id": "project_core"
}
```

#### Response Structure
```json
{
  "message": "fix(notifier): sanitize notification channel identifier\n\nEnsure background notification payload matches Windows toast schema constraints.",
  "provider": "gemini"
}
```

---

## Keyboard Shortcuts

| Shortcut | Scope | Action |
|---|---|---|
| `r` | Global | Trigger manual refresh across all monitored repositories |
| `n` | Global | Toggle the notification history drawer |
| `Escape` | Modals / Views | Close active modal or return to the overview grid |

---

## Design System & Interaction Standards

GitPulse's user interface is engineered according to the motion and interaction philosophy of **Emil Kowalski**:

- **Predictable Easing Curves:** Micro-interactions utilize `--ease-out: cubic-bezier(0.23, 1, 0.32, 1)` for entrances and expansion, preventing linear robotic transitions.
- **Tactile Physics:** Interactive buttons incorporate physical feedback via `:active { transform: scale(0.97); }`.
- **Sonner-Style Stacked Toasts:** Dynamic alerts stack gracefully in the bottom-right corner with fluid exit and entrance animations, handling `.success()`, `.error()`, `.warning()`, and `.promise()` states.
- **Clean Iconography:** Uses pure SVG vector icons from [Lucide](https://lucide.dev/) for crisp presentation across high-DPI displays.

---

## Security & Local-First Guarantee

- **Local Execution:** GitPulse executes strictly on your local loopback interface (`127.0.0.1`). No codebase files, repository names, or local directory structures are ever transmitted to third-party servers.
- **Zero Telemetry:** The application contains no analytics, usage telemetry, or remote tracking scripts.
- **API Key Isolation:** External network communication occurs exclusively when you explicitly trigger **"Generate AI Message"**, sending only the relevant code diff snippet directly to your configured provider (Google Gemini or OpenAI). Keys remain in your local `.env` and are never committed.
- **Credential Delegation:** Git operations inherit your existing system Git authentication (SSH agents, Git Credential Manager, or GPG keys) without capturing private credentials.

---

## Troubleshooting

### Port 8765 Already in Use
If another process is bound to port `8765`, specify a different port when launching:
```bash
uvicorn app.py:app --host 127.0.0.1 --port 8899
```

### Git Credential Prompts on Push
If `push` fails with an authentication error:
1. Confirm that `git push` succeeds from your terminal for that repository.
2. Verify that your Git credential helper is configured:
   ```bash
   git config --global credential.helper manager
   ```

### Windows "Dubious Ownership" or Safe Directory Warnings
If a repository displays an ownership error:
```bash
git config --global --add safe.directory /path/to/your/repository
```

---

## Contributing

Contributions are welcome. To contribute:

1. Fork the repository.
2. Create a focused feature branch:
   ```bash
   git checkout -b feature/issue-description
   ```
3. Commit your changes using conventional commit messages:
   ```bash
   git commit -m "feat(tree): add file search filter"
   ```
4. Push to your branch:
   ```bash
   git push origin feature/issue-description
   ```
5. Open a Pull Request detailing your changes and test coverage.

---

## License

This project is licensed under the [MIT License](LICENSE).
