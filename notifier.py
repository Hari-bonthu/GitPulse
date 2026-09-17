import threading
import time
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional
import uuid

try:
    from plyer import notification
except ImportError:
    notification = None

class NotificationManager:
    def __init__(self, config_path: str):
        self.config_path = Path(config_path)
        self.state_path = self.config_path.parent / "notification_state.json"
        self._load_config()
        
    def _load_config(self):
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
        except Exception:
            self.config = {"settings": {}}
            
    def _get_notification_state(self) -> Dict:
        try:
            if self.state_path.exists():
                with open(self.state_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception:
            pass
        return {"notified_repos": {}, "history": []}
        
    def _save_notification_state(self, state: Dict):
        try:
            with open(self.state_path, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=2)
        except Exception:
            pass

    def _is_quiet_hours(self) -> bool:
        settings = self.config.get('settings', {})
        start = settings.get('notification_quiet_start', "22:00")
        end = settings.get('notification_quiet_end', "08:00")
        if not start or not end:
            return False
            
        try:
            now = datetime.now()
            current = now.time()
            start_time = datetime.strptime(start, "%H:%M").time()
            end_time = datetime.strptime(end, "%H:%M").time()
            
            if start_time < end_time:
                return start_time <= current <= end_time
            else:
                return current >= start_time or current <= end_time
        except Exception:
            return False

    def send_notification(self, title: str, message: str):
        if self._is_quiet_hours():
            return
            
        if notification:
            try:
                notification.notify(
                    title=title,
                    message=message,
                    app_name="GitPulse",
                    timeout=5
                )
            except Exception:
                pass
                
        state = self._get_notification_state()
        state['history'].append({
            "id": str(uuid.uuid4()),
            "title": title,
            "message": message,
            "timestamp": datetime.now().isoformat(),
            "read": False
        })
        self._save_notification_state(state)

    def check_and_notify(self, repo_summaries: list):
        if self._is_quiet_hours():
            return
            
        state = self._get_notification_state()
        now = datetime.now()
        
        for repo in repo_summaries:
            repo_id = getattr(repo, 'id', None) or (repo.get('id') if isinstance(repo, dict) else None)
            health = getattr(repo, 'health', None) or (repo.get('health') if isinstance(repo, dict) else None)
            name = getattr(repo, 'name', None) or (repo.get('name') if isinstance(repo, dict) else None)
            if not repo_id:
                continue
            repo_state = state['notified_repos'].get(repo_id, {})
            
            if health == 'DIRTY':
                last_dirty = repo_state.get('last_dirty_notify')
                if not last_dirty or (now - datetime.fromisoformat(last_dirty)).days >= 1:
                    self.send_notification("Uncommitted Changes", f"{name} has uncommitted changes.")
                    repo_state['last_dirty_notify'] = now.isoformat()
            
            elif health == 'UNPUSHED':
                last_unpushed = repo_state.get('last_unpushed_notify')
                if not last_unpushed or (now - datetime.fromisoformat(last_unpushed)).days >= 1:
                    self.send_notification("Unpushed Commits", f"{name} has commits that need pushing.")
                    repo_state['last_unpushed_notify'] = now.isoformat()
            
            elif health == 'STALE':
                last_stale = repo_state.get('last_stale_notify')
                if not last_stale or (now - datetime.fromisoformat(last_stale)).days >= 1:
                    self.send_notification("Stale Repository", f"{name} hasn't been updated recently.")
                    repo_state['last_stale_notify'] = now.isoformat()
                    
            state['notified_repos'][repo_id] = repo_state
            
        self._save_notification_state(state)

    def get_pending_notifications(self) -> List[Dict]:
        state = self._get_notification_state()
        return [n for n in state.get('history', []) if not n.get('read', False)]

    def clear_notification(self, notification_id: str):
        state = self._get_notification_state()
        for n in state.get('history', []):
            if n['id'] == notification_id:
                n['read'] = True
        self._save_notification_state(state)


class NotificationScheduler:
    def __init__(self, config_path: Optional[str] = None):
        if not config_path:
            config_path = str(Path(__file__).parent / "config.json")
        self.manager = NotificationManager(config_path)
        self.stop_event = threading.Event()
        self.thread = None

    def start(self, scan_func, interval_seconds: int = 300):
        def loop():
            while not self.stop_event.is_set():
                try:
                    summaries = scan_func()
                    self.manager.check_and_notify(summaries)
                except Exception:
                    pass
                self.stop_event.wait(interval_seconds)
                
        self.stop_event.clear()
        self.thread = threading.Thread(target=loop, daemon=True)
        self.thread.start()

    def stop(self):
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=2.0)
