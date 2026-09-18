"""
GitPulse — AI & Semantic Conventional Commit Message Generator
Supports Google Gemini, OpenAI, and an Intelligent Local Semantic Engine.
"""

import os
import re
import json
from typing import Tuple, List, Optional, Dict
import urllib.request
import urllib.error
from dotenv import load_dotenv

load_dotenv()


def generate_semantic_commit_message(diff_text: str, changed_files: Optional[List[str]] = None) -> str:
    """
    Intelligent heuristic diff & file analyzer that produces
    accurate, human-crafted conventional commit messages tailored to the repo state.
    Format: <type>(<scope>): <description> (under 72 chars)
    """
    files = changed_files or []
    if not files and diff_text:
        matches = re.findall(r"diff --git a/(.+?) b/(.+)", diff_text)
        if matches:
            files = list(dict.fromkeys([m[1] for m in matches]))
        else:
            untracked = re.findall(r"\+\s+([^\r\n]+)", diff_text)
            if untracked:
                files = [u.strip() for u in untracked if u.strip()]

    if not files:
        files = ["repository files"]

    # File categorization
    has_ui = any("static/" in f or f.endswith((".html", ".js")) for f in files)
    has_styles = any(f.endswith(".css") for f in files)
    has_backend = any(f in ("app.py", "git_scanner.py", "notifier.py", "models.py") or (f.endswith(".py") and not "ai_commit" in f) for f in files)
    has_ai = any("ai_commit" in f for f in files)
    has_docs = any(f.endswith((".md", ".txt")) or "doc" in f.lower() for f in files)
    has_config = any(f in (".gitignore", "config.json", "config.example.json", ".env", "requirements.txt") or f.endswith((".bat", ".sh", ".json")) for f in files)

    diff_lower = diff_text.lower() if diff_text else ""

    # Detect high-signal domain actions
    actions = []
    if "custom-select" in diff_lower or "setupcustomselect" in diff_lower or "custom select" in diff_lower:
        actions.append("custom select components")
    if "overflow" in diff_lower or "popoverup" in diff_lower or "popoverdown" in diff_lower:
        actions.append("dropdown clipping fixes")
    if "git-tree" in diff_lower or "checkbox" in diff_lower or "stagedfiles" in diff_lower:
        actions.append("git tree styling")
    if "generate_commit" in diff_lower or "gemini" in diff_lower or "ai_commit" in diff_lower:
        actions.append("AI commit generator")
    if "theme-dark" in diff_lower or "theme-light" in diff_lower or "theme" in diff_lower:
        actions.append("theme tokens")
    if ".gitignore" in files or "config.example.json" in files:
        actions.append("project configuration")
    if any(f.lower().startswith("readme") for f in files):
        actions.append("documentation")

    # Determine type
    if any(term in diff_lower for term in ["fix", "error", "bug", "syntaxerror", "overflow: visible"]):
        commit_type = "fix"
    elif has_ui and (actions or "button" in diff_lower or "modal" in diff_lower):
        commit_type = "feat"
    elif has_styles and not has_backend and not has_ui:
        commit_type = "style"
    elif has_docs and len(files) == 1:
        commit_type = "docs"
    elif has_config and not has_ui and not has_backend:
        commit_type = "chore"
    elif has_backend and not has_ui:
        commit_type = "refactor"
    else:
        commit_type = "feat"

    # Determine scope
    if has_ui and has_styles:
        scope = "ui"
    elif has_styles and not has_ui:
        scope = "style"
    elif has_ai:
        scope = "ai"
    elif has_backend and has_ui:
        scope = "app"
    elif has_backend:
        scope = "api"
    elif has_docs:
        scope = "docs"
    elif has_config:
        scope = "config"
    else:
        primary_name = os.path.splitext(os.path.basename(files[0]))[0]
        scope = primary_name if primary_name and len(primary_name) < 12 else "core"

    # Compose description
    if actions:
        if len(actions) == 1:
            desc = f"enhance {actions[0]}"
        elif len(actions) == 2:
            desc = f"add {actions[0]} and {actions[1]}"
        else:
            desc = f"update {actions[0]} and {actions[1]}"
    else:
        base_names = [os.path.basename(f) for f in files[:2]]
        if len(files) == 1:
            desc = f"update {base_names[0]}"
        elif len(files) == 2:
            desc = f"update {base_names[0]} and {base_names[1]}"
        else:
            desc = f"update {base_names[0]} and {len(files) - 1} other files"

    # Polish commit message
    if commit_type == "fix" and "dropdown clipping fixes" in actions:
        desc = "resolve menu overflow clipping and focus outline"
    elif commit_type == "feat" and "custom select components" in actions and "git tree styling" in actions:
        desc = "add custom select dropdowns and refine git tree styling"

    msg = f"{commit_type}({scope}): {desc}"
    if len(msg) > 72:
        msg = msg[:72].rstrip()
    return msg


def generate_commit_message_gemini(diff_text: str, api_key: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Calls Google Gemini API. Returns (message, None) on success or (None, error_str) on failure.
    """
    if not api_key:
        return None, "No Gemini API key provided"

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
    prompt = f"""Analyze this git diff and generate a concise conventional commit message.
Format: <type>(<optional scope>): <description>
Types: feat, fix, docs, style, refactor, test, chore, perf, ci, build
Rules:
- Keep description under 72 characters
- Use imperative mood ("add" not "added")
- Be specific about what changed
- Return ONLY the commit message line, no backticks, no markdown.

Diff:
{diff_text}"""

    data = {
        "contents": [{"parts": [{"text": prompt}]}]
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            res_body = response.read().decode("utf-8")
            res_json = json.loads(res_body)
            msg = res_json["candidates"][0]["content"]["parts"][0]["text"].strip()
            msg = msg.strip("`").strip()
            lines = [l.strip() for l in msg.splitlines() if l.strip()]
            return (lines[0] if lines else msg), None
    except urllib.error.HTTPError as e:
        err_msg = f"HTTP {e.code}"
        if e.code == 401:
            err_msg = "Invalid API key"
        elif e.code == 429:
            err_msg = "Rate limit exceeded"
        return None, err_msg
    except urllib.error.URLError:
        return None, "Network error"
    except Exception as e:
        return None, str(e)


def generate_commit_message_openai(diff_text: str, api_key: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Calls OpenAI API. Returns (message, None) on success or (None, error_str) on failure.
    """
    if not api_key:
        return None, "No OpenAI API key provided"

    url = "https://api.openai.com/v1/chat/completions"
    prompt = f"""Analyze this git diff and generate a concise conventional commit message.
Format: <type>(<optional scope>): <description>
Types: feat, fix, docs, style, refactor, test, chore, perf, ci, build
Rules:
- Under 72 characters
- Imperative mood
- Return ONLY the commit message line, no extra text.

Diff:
{diff_text}"""

    data = {
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            res_body = response.read().decode("utf-8")
            res_json = json.loads(res_body)
            msg = res_json["choices"][0]["message"]["content"].strip()
            msg = msg.strip("`").strip()
            lines = [l.strip() for l in msg.splitlines() if l.strip()]
            return (lines[0] if lines else msg), None
    except urllib.error.HTTPError as e:
        err_msg = f"HTTP {e.code}"
        if e.code == 401:
            err_msg = "Invalid API key"
        elif e.code == 429:
            err_msg = "Quota exhausted"
        return None, err_msg
    except urllib.error.URLError:
        return None, "Network error"
    except Exception as e:
        return None, str(e)


def generate_commit_message(
    diff_text: str,
    provider: str = "gemini",
    api_key: Optional[str] = None,
    changed_files: Optional[List[str]] = None
) -> Tuple[str, str]:
    """
    Main entrypoint: generates commit message via requested LLM provider,
    or falls back to the smart semantic rule engine with clear, truthful status reporting.
    """
    diff_snippet = diff_text[:5000] if diff_text else ""
    semantic_fallback = generate_semantic_commit_message(diff_text, changed_files)

    # 1. Resolve API key
    key = api_key
    if not key:
        if provider == "gemini":
            key = os.environ.get("GEMINI_API_KEY")
        elif provider == "openai":
            key = os.environ.get("OPENAI_API_KEY")

    # 2. Try Gemini
    if provider == "gemini":
        if key and key.strip():
            msg, err = generate_commit_message_gemini(diff_snippet, key.strip())
            if msg:
                return msg, "Google Gemini"
            return semantic_fallback, f"Smart Engine ({err})"
        return semantic_fallback, "Smart Engine (No Gemini key)"

    # 3. Try OpenAI
    elif provider == "openai":
        if key and key.strip():
            msg, err = generate_commit_message_openai(diff_snippet, key.strip())
            if msg:
                return msg, "OpenAI"
            return semantic_fallback, f"Smart Engine ({err})"
        return semantic_fallback, "Smart Engine (No OpenAI key)"

    # 4. Smart Engine direct
    return semantic_fallback, "Smart Engine"
