"""承诺装置 — 小静 R4"""

from datetime import datetime, timedelta
from typing import Optional
from .preferences import PreferenceManager


class CommitmentDevice:
    def __init__(self, pref_manager: PreferenceManager):
        self.pref_manager = pref_manager
        self._exit_requested_at: Optional[datetime] = None
        self._audit_log: list = []
    
    def request_exit(self) -> dict:
        prefs = self.pref_manager.get_preferences()
        lock = prefs.commitment_lock_strength
        cooldown = prefs.exit_cooldown_hours
        self._log("exit_requested", {"lock": lock, "cooldown": cooldown})
        if lock == "none":
            return {"allowed": True, "message": "你可以随时退出。数据会被保留。"}
        elif lock == "light":
            return {"allowed": True, "warning": True,
                    "message": "你可以退出。提醒：你已积累了认知记录，确定退出？"}
        elif lock == "medium":
            if self._exit_requested_at is None:
                self._exit_requested_at = datetime.now()
                return {"allowed": False,
                        "message": f"退出需要 {cooldown} 小时冷却期。这是你过去的自己设定的保护措施。",
                        "cooldown_active": True}
            else:
                elapsed = (datetime.now() - self._exit_requested_at).total_seconds() / 3600
                if elapsed >= cooldown:
                    self._exit_requested_at = None
                    return {"allowed": True, "message": "冷却期已结束。"}
                else:
                    return {"allowed": False, "message": f"还需要等待 {cooldown - elapsed:.1f} 小时。", "cooldown_active": True}
        elif lock == "heavy":
            return {"allowed": False,
                    "message": f"退出需要信任人确认。信任人：{prefs.trusted_contact or '未设置'}。",
                    "requires_trusted_confirmation": True}
        return {"allowed": True, "message": ""}
    
    def confirm_exit_by_trusted(self) -> dict:
        self._log("exit_confirmed_by_trusted", {})
        return {"allowed": True, "message": "信任人已确认。你可以退出了。"}
    
    def get_audit_log(self) -> list:
        return self._audit_log
    
    def _log(self, action: str, details: dict):
        self._audit_log.append({"action": action, "details": details, "timestamp": datetime.now().isoformat()})