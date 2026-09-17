import os
import json
from typing import Tuple
import urllib.request
import urllib.error
from dotenv import load_dotenv

load_dotenv()

def get_ai_provider() -> Tuple[str, str]:
    gemini_key = os.environ.get("GEMINI_API_KEY")
    if gemini_key:
        return "gemini", gemini_key
    openai_key = os.environ.get("OPENAI_API_KEY")
    if openai_key:
        return "openai", openai_key
    return "none", ""

def generate_commit_message_gemini(diff_text: str, api_key: str) -> str:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
    prompt = f"""Analyze this git diff and generate a concise conventional commit message.
Format: <type>(<optional scope>): <description>
Types: feat, fix, docs, style, refactor, test, chore, perf, ci, build
Rules:
- Keep the description under 72 characters
- Use imperative mood ("add" not "added")
- Be specific about what changed
- If multiple changes, summarize the primary change

Diff:
{diff_text}

Respond with ONLY the commit message, nothing else."""

    data = {
        "contents": [{"parts": [{"text": prompt}]}]
    }
    
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode('utf-8'),
        headers={'Content-Type': 'application/json'},
        method='POST'
    )
    
    try:
        with urllib.request.urlopen(req) as response:
            res_body = response.read().decode('utf-8')
            res_json = json.loads(res_body)
            try:
                msg = res_json['candidates'][0]['content']['parts'][0]['text']
                return msg.strip()
            except (KeyError, IndexError):
                return "Update files"
    except Exception:
        return "Update files"

def generate_commit_message_openai(diff_text: str, api_key: str) -> str:
    url = "https://api.openai.com/v1/chat/completions"
    prompt = f"""Analyze this git diff and generate a concise conventional commit message.
Format: <type>(<optional scope>): <description>
Types: feat, fix, docs, style, refactor, test, chore, perf, ci, build
Rules:
- Keep the description under 72 characters
- Use imperative mood ("add" not "added")
- Be specific about what changed
- If multiple changes, summarize the primary change

Diff:
{diff_text}

Respond with ONLY the commit message, nothing else."""

    data = {
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3
    }
    
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode('utf-8'),
        headers={
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {api_key}'
        },
        method='POST'
    )
    
    try:
        with urllib.request.urlopen(req) as response:
            res_body = response.read().decode('utf-8')
            res_json = json.loads(res_body)
            try:
                msg = res_json['choices'][0]['message']['content']
                return msg.strip()
            except (KeyError, IndexError):
                return "Update files"
    except Exception:
        return "Update files"

def generate_commit_message(diff_text: str) -> Tuple[str, str]:
    if not diff_text:
        return "Update files", "none"
        
    diff_text = diff_text[:4000]
    provider, key = get_ai_provider()
    
    if provider == "gemini":
        return generate_commit_message_gemini(diff_text, key), "gemini"
    elif provider == "openai":
        return generate_commit_message_openai(diff_text, key), "openai"
    else:
        from datetime import datetime
        return f"Update files — {datetime.now().strftime('%Y-%m-%d')}", "none"
