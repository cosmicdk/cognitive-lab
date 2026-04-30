"""用户偏好管理 — 控制面板实现（R3）"""

from datetime import datetime
from .models import UserPreferences
from storage.database import Database


class PreferenceManager:
    PREFERENCE_KEY = "user_preferences"
    
    def __init__(self, db: Database):
        self.db = db
        self._ensure_defaults()
    
    def _ensure_defaults(self):
        existing = self.db.get_preference(self.PREFERENCE_KEY)
        if not existing:
            defaults = UserPreferences()
            self.db.set_preference(self.PREFERENCE_KEY, defaults.to_dict())
    
    def get_preferences(self) -> UserPreferences:
        data = self.db.get_preference(self.PREFERENCE_KEY)
        if not data: return UserPreferences()
        return UserPreferences.from_dict(data)
    
    def update_preferences(self, **kwargs) -> UserPreferences:
        current = self.get_preferences()
        current_dict = current.to_dict()
        current_dict.update(kwargs)
        new_prefs = UserPreferences.from_dict(current_dict)
        self.db.set_preference(self.PREFERENCE_KEY, new_prefs.to_dict())
        return new_prefs
    
    def reset_to_defaults(self) -> UserPreferences:
        defaults = UserPreferences()
        self.db.set_preference(self.PREFERENCE_KEY, defaults.to_dict())
        return defaults
    
    def get_interference_settings(self) -> dict:
        prefs = self.get_preferences()
        return {"enabled": prefs.interference_enabled, "intensity": prefs.interference_intensity,
                "domains": prefs.interference_domains, "mode": prefs.interference_mode}
    
    def set_interference(self, enabled: bool = None, intensity: float = None,
                         domains: list = None, mode: str = None) -> UserPreferences:
        updates = {}
        if enabled is not None: updates["interference_enabled"] = enabled
        if intensity is not None: updates["interference_intensity"] = max(0.0, min(1.0, intensity))
        if domains is not None: updates["interference_domains"] = domains
        if mode is not None and mode in ("on_request", "on_pattern", "on_conclusion"):
            updates["interference_mode"] = mode
        return self.update_preferences(**updates)
    
    def get_commitment_settings(self) -> dict:
        prefs = self.get_preferences()
        return {"lock_strength": prefs.commitment_lock_strength,
                "cooldown_hours": prefs.exit_cooldown_hours, "trusted_contact": prefs.trusted_contact}