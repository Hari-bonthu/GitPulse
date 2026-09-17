# GitPulse ⚡

**Multi-Repo Git Tracking Dashboard** — Track the git status of all your projects from one place.

## Features

- **Dashboard Overview** — Card grid showing all tracked repos with health status
- **Git Tree View** — IDE-style collapsible file tree with staging checkboxes
- **Diff Preview** — Click any file to see inline syntax-highlighted diffs
- **Git Stash Management** — View, apply, pop, and drop stash entries
- **Smart Commit** — Dropdown with "Commit" and "Commit & Push" options
- **AI Commit Messages** — Generate commit messages via Google Gemini or OpenAI
- **Desktop Notifications** — Alerts when repos need attention
- **Auto-refresh** — Configurable polling interval (30s / 60s / 5min)
- **Dark/Light Theme** — Follows system preference or manual override

## Quick Start

### 1. Install Dependencies

```bash
cd C:\Users\DELL\Desktop\GitPulse
pip install -r requirements.txt
```

### 2. Configure AI (Optional)

Copy `.env.example` to `.env` and add your API key:

```bash
copy .env.example .env
```

Edit `.env`:
```env
GEMINI_API_KEY=your_gemini_api_key_here
```

Get a free Gemini API key at: https://aistudio.google.com/apikey

### 3. Run

```bash
python app.py
```

Open **http://localhost:8765** in your browser.

### 4. Add Repositories

Click **"Add Repository"** in the sidebar and paste the full path to any git repo:

```
C:\Users\DELL\Projects\my-app
C:\Users\DELL\Projects\api-server
```

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `r` | Refresh dashboard |
| `n` | Toggle notifications |
| `Escape` | Close modal / Go back |

## API Documentation

Interactive API docs available at: **http://localhost:8765/docs**

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Backend | Python + FastAPI |
| Git Operations | GitPython |
| AI Commit Messages | Google Gemini / OpenAI (via HTTP) |
| Frontend | Vanilla HTML + CSS + JS |
| Icons | Lucide Icons |
| Notifications | Plyer (desktop toasts) |

## Project Structure

```
GitPulse/
├── app.py              # FastAPI server
├── git_scanner.py      # Git scanning logic
├── ai_commit.py        # AI commit message generation
├── notifier.py         # Desktop notifications
├── models.py           # Pydantic data models
├── config.json         # Repo paths & settings
├── .env                # API keys (gitignored)
├── .env.example        # API key template
├── requirements.txt    # Dependencies
└── static/
    ├── index.html      # Dashboard UI
    ├── styles.css      # Custom styles
    └── app.js          # Frontend logic
```

## License

MIT
