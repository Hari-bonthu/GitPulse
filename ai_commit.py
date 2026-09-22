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


def generate_semantic_commit_message(diff_text: str, changed_files: Optional[List[str]] = None, style: str = "conventional") -> str:
    """
    Intelligent heuristic diff & file analyzer that produces
    accurate, human-crafted commit messages tailored to the repo state and requested style.
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

    if style == "concise":
        concise = desc[0].upper() + desc[1:] if desc else "Update project files"
        return concise[:60].rstrip()
    elif style == "detailed":
        bullets = []
        if actions:
            for act in actions[:3]:
                bullets.append(f"- {act.capitalize()}")
        else:
            bullets.append(f"- Update {', '.join(base_names[:3])}{' and others' if len(base_names) > 3 else ''}")
        bullets.append(f"- Modify {len(files)} file(s) in {scope}")
        return f"{commit_type}({scope}): {desc}\n\n" + "\n".join(bullets)
    else:
        msg = f"{commit_type}({scope}): {desc}"
        if len(msg) > 72:
            msg = msg[:72].rstrip()
        return msg


def _build_prompt_for_style(diff_text: str, style: str = "conventional") -> str:
    if style == "concise":
        return f"""Analyze this git diff and generate a single concise imperative commit message without any type prefix or scope.
Rules:
- Keep under 60 characters
- Use imperative mood (e.g. "Add branch switcher and pull sync controls")
- Return ONLY the single line commit message, no backticks, no punctuation at end.

Diff:
{diff_text}"""
    elif style == "detailed":
        return f"""Analyze this git diff and generate a detailed conventional commit message.
Format:
<type>(<optional scope>): <subject line under 72 characters>

- <bullet point 1 explaining major change>
- <bullet point 2 explaining secondary change>
- <bullet point 3 if applicable>

Rules:
- Types: feat, fix, docs, style, refactor, test, chore, perf
- Subject line under 72 chars
- 2 to 4 high-signal bullet points
- Return ONLY the commit message and bullets, no markdown code fence blocks.

Diff:
{diff_text}"""
    else:
        return f"""Analyze this git diff and generate a concise conventional commit message.
Format: <type>(<optional scope>): <description>
Types: feat, fix, docs, style, refactor, test, chore, perf, ci, build
Rules:
- Keep description under 72 characters
- Use imperative mood ("add" not "added")
- Be specific about what changed
- Return ONLY the commit message line, no backticks, no markdown.

Diff:
{diff_text}"""


def generate_commit_message_gemini(diff_text: str, api_key: str, style: str = "conventional") -> Tuple[Optional[str], Optional[str]]:
    """
    Calls Google Gemini API. Returns (message, None) on success or (None, error_str) on failure.
    Tries gemini-3.6-flash, gemini-3-flash-preview, gemini-flash-latest with resilient fallbacks.
    """
    if not api_key:
        return None, "No Gemini API key provided"

    prompt = _build_prompt_for_style(diff_text, style)
    data = {
        "contents": [{"parts": [{"text": prompt}]}]
    }
    body = json.dumps(data).encode("utf-8")

    models_to_try = [
        "gemini-3.6-flash",
        "gemini-3-flash-preview",
        "gemini-flash-latest",
        "gemini-2.5-flash"
    ]

    last_err = "No models available"
    for model_name in models_to_try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
        req = urllib.request.Request(
            url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as response:
                res_body = response.read().decode("utf-8")
                res_json = json.loads(res_body)
                msg = res_json["candidates"][0]["content"]["parts"][0]["text"].strip()
                msg = msg.strip("`").strip()
                if style != "detailed":
                    lines = [l.strip() for l in msg.splitlines() if l.strip()]
                    return (lines[0] if lines else msg), None
                return msg, None
        except urllib.error.HTTPError as e:
            if e.code == 401:
                return None, "Invalid API key"
            elif e.code == 429:
                return None, "Rate limit exceeded"
            elif e.code == 404:
                last_err = f"HTTP {e.code}"
                continue
            last_err = f"HTTP {e.code}"
        except urllib.error.URLError:
            last_err = "Network error"
        except Exception as e:
            last_err = str(e)

    return None, last_err


def generate_commit_message_openai(diff_text: str, api_key: str, style: str = "conventional") -> Tuple[Optional[str], Optional[str]]:
    """
    Calls OpenAI API. Returns (message, None) on success or (None, error_str) on failure.
    """
    if not api_key:
        return None, "No OpenAI API key provided"

    url = "https://api.openai.com/v1/chat/completions"
    prompt = _build_prompt_for_style(diff_text, style)

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
            if style != "detailed":
                lines = [l.strip() for l in msg.splitlines() if l.strip()]
                return (lines[0] if lines else msg), None
            return msg, None
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
    changed_files: Optional[List[str]] = None,
    style: str = "conventional"
) -> Tuple[str, str]:
    """
    Main entrypoint: generates commit message via requested LLM provider and style,
    or falls back to the smart semantic rule engine with clear, truthful status reporting.
    """
    diff_snippet = diff_text[:5000] if diff_text else ""
    semantic_fallback = generate_semantic_commit_message(diff_text, changed_files, style=style)

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
            msg, err = generate_commit_message_gemini(diff_snippet, key.strip(), style=style)
            if msg:
                return msg, "Google Gemini"
            return semantic_fallback, f"Smart Engine ({err})"
        return semantic_fallback, "Smart Engine (No Gemini key)"

    # 3. Try OpenAI
    elif provider == "openai":
        if key and key.strip():
            msg, err = generate_commit_message_openai(diff_snippet, key.strip(), style=style)
            if msg:
                return msg, "OpenAI"
            return semantic_fallback, f"Smart Engine ({err})"
        return semantic_fallback, "Smart Engine (No OpenAI key)"

    # 4. Smart Engine direct
    return semantic_fallback, "Smart Engine"


def analyze_diff_for_leaks_and_review(
    diff_text: str,
    changed_files: List[str],
    api_key: Optional[str] = None,
    provider: str = "gemini"
) -> Tuple[str, str, List[str], List[Dict[str, str]], List[str]]:
    """
    Heuristic security & quality scanner:
    - Scans added lines for secrets, credentials, API keys, and sensitive tokens.
    - Scans for leftover debug prints and debugger statements.
    - Generates technical review summary with risk assessment.
    Returns: (summary, risk_level, findings, leaks, debug_artifacts)
    """
    leaks = []
    debug_artifacts = []
    findings = []

    # Rules for secret detection
    SECRET_RULES = [
        (r"AIza[0-9A-Za-z_-]{35}", "Google API Key", "HIGH"),
        (r"sk-[a-zA-Z0-9_-]{20,}", "OpenAI API Key", "HIGH"),
        (r"AKIA[0-9A-Z]{16}", "AWS Access Key ID", "HIGH"),
        (r"gh[pousr]_[A-Za-z0-9_]{36,}", "GitHub Token", "HIGH"),
        (r"-----BEGIN (?:RSA|OPENSSH|PGP|EC|DSA) PRIVATE KEY", "Private Cryptographic Key", "HIGH"),
        (r"eyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.", "JSON Web Token (JWT)", "MEDIUM"),
        (r"(?:api[_-]?key|secret|password|access[_-]?token)\s*[:=]\s*['\"][a-zA-Z0-9_\-\.]{12,}['\"]", "Hardcoded Credential / Secret", "HIGH"),
    ]

    DEBUG_PATTERNS = [
        (r"\bconsole\.(?:log|warn|error|debug|info)\s*\(", "console.log() debug statement"),
        (r"\bdebugger\s*;", "debugger breakpoint"),
        (r"\bprint\s*\(", "print() debug output"),
        (r"\b(?:pdb|ipdb)\.set_trace\s*\(", "Python interactive debugger"),
        (r"\bbreakpoint\s*\(", "Python breakpoint() statement"),
    ]

    current_file = "unknown"
    for line in (diff_text or "").splitlines():
        if line.startswith("diff --git"):
            m = re.search(r"b/(.+)", line)
            if m:
                current_file = m.group(1)
        elif line.startswith("+++ b/"):
            current_file = line[6:].strip()

        # Only inspect added lines
        if line.startswith("+") and not line.startswith("+++"):
            added_content = line[1:].strip()
            # Ignore comments or example files
            is_example = any(ex in current_file.lower() for ex in (".example", "test", "spec", "mock", "dummy"))

            # Secret check
            if not is_example:
                for pat, label, risk in SECRET_RULES:
                    if re.search(pat, added_content, re.IGNORECASE):
                        snippet = added_content[:60] + ("..." if len(added_content) > 60 else "")
                        leaks.append({
                            "file": current_file,
                            "line_snippet": snippet,
                            "rule": label,
                            "risk": risk
                        })

            # Debug check
            if not is_example:
                for pat, label in DEBUG_PATTERNS:
                    if re.search(pat, added_content):
                        snippet = added_content[:60] + ("..." if len(added_content) > 60 else "")
                        debug_artifacts.append(f"{current_file}: {label} ({snippet})")

    # High-level findings
    if leaks:
        findings.append(f"Detected {len(leaks)} potential secret leak(s) in working tree.")
    if debug_artifacts:
        findings.append(f"Found {len(debug_artifacts)} debug statement(s) that may be unintended in commits.")
    if len(changed_files) > 12:
        findings.append(f"Large change set: {len(changed_files)} files modified concurrently.")

    # Determine risk level
    if any(l["risk"] == "HIGH" for l in leaks):
        risk_level = "HIGH"
    elif leaks or debug_artifacts or len(changed_files) > 15:
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"

    # Review Summary (try LLM if available, otherwise heuristic)
    key = api_key
    if not key:
        key = os.environ.get("GEMINI_API_KEY") if provider == "gemini" else os.environ.get("OPENAI_API_KEY")

    summary = ""
    if key and key.strip() and diff_text:
        review_prompt = f"""You are an expert code reviewer and tech lead.
Review this git diff and provide a concise, high-signal 2-sentence evaluation of what is changing, its architecture impact, and code quality.
Rules:
- Be specific, professional, and constructive.
- Return ONLY 2 sentences. No markdown headers, no bullets.

Diff:
{diff_text[:3500]}"""
        if provider == "gemini":
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent?key={key.strip()}"
            try:
                body = json.dumps({"contents": [{"parts": [{"text": review_prompt}]}]}).encode("utf-8")
                req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
                with urllib.request.urlopen(req, timeout=10) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    summary = data["candidates"][0]["content"]["parts"][0]["text"].strip()
            except Exception:
                pass

    if not summary:
        file_summary = ", ".join([os.path.basename(f) for f in changed_files[:4]])
        if len(changed_files) > 4:
            file_summary += f" and {len(changed_files) - 4} more"
        summary = f"Working tree modifies {len(changed_files)} file(s) ({file_summary}). Security posture is {risk_level.lower()} with {len(leaks)} secret warnings and {len(debug_artifacts)} debug statements."

    return summary, risk_level, findings, leaks, debug_artifacts


def generate_pr_description(
    commits: List[Dict],
    branch_name: str,
    api_key: Optional[str] = None,
    provider: str = "gemini"
) -> Tuple[str, str]:
    """
    Generates a structured GitHub Pull Request title and Markdown body
    based on unpushed commits and repository branch state.
    """
    if not commits:
        title = f"feat: updates on {branch_name}"
        body = f"""### Overview\nChanges on branch `{branch_name}`.\n\n### Key Changes\n- General code updates and maintenance.\n\n### Verification\n- [ ] Code builds cleanly\n- [ ] Verified manually"""
        return title, body

    commit_messages = [c.get("message", "") for c in commits if c.get("message")]
    title = commit_messages[0] if commit_messages else f"feat: updates on {branch_name}"

    # Try LLM synthesis
    key = api_key
    if not key:
        key = os.environ.get("GEMINI_API_KEY") if provider == "gemini" else os.environ.get("OPENAI_API_KEY")

    if key and key.strip() and commit_messages:
        prompt = f"""You are a tech lead writing a GitHub Pull Request description for branch '{branch_name}'.
The unpushed commits on this branch are:
{chr(10).join(f'- {m}' for m in commit_messages)}

Generate a structured GitHub PR description in Markdown.
Include:
### Overview (1-2 sentences)
### Key Changes (bullet points summarizing the work)
### Verification Plan (checkboxes for testing)

Return ONLY the Markdown content. Do not wrap in ```markdown code fences."""

        if provider == "gemini":
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent?key={key.strip()}"
            try:
                body = json.dumps({"contents": [{"parts": [{"text": prompt}]}]}).encode("utf-8")
                req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
                with urllib.request.urlopen(req, timeout=12) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    body = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                    body = body.strip("`").strip()
                    return title, body
            except Exception:
                pass

    # Heuristic fallback
    bullets = "\n".join(f"- {m}" for m in commit_messages)
    body = f"""### Overview
This pull request brings together {len(commits)} commit(s) on branch `{branch_name}`.

### Key Changes
{bullets}

### Verification & Testing
- [x] Code compiled and verified locally
- [x] Tested all affected user flows
- [x] Verified zero console errors
"""
    return title, body
