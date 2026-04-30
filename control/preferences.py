"""用户偏好管理 — 控制面板实现（R3）

用户可以完全控制：
- 干涉开关和强度
- 干涉领域（哪些领域主动干涉）
- 认知母语风格
- 数据保留策略
- 实验室模式参数
"""

from datetime import datetime
from core.models import UserPreferences
from storage.database import Database


class PreferenceManager:
    """用户偏好管理器"""
    
    PREFERENCE_KEY = "user_preferences"
    
    def __init__(self, db: Database):
        self.db = db
        self._ensure_defaults()
    
    def _ensure_defaults(self):
        """确保有默认偏好设置"""
        existing = self.db.get_preference(self.PREFERENCE_KEY)
        if not existing:
            defaults = UserPreferences()
            self.db.set_preference(self.PREFERENCE_KEY, defaults.to_dict())
    
    def get_preferences(self) -> UserPreferences:
        """获取当前用户偏好"""
        data = self.db.get_preference(self.PREFERENCE_KEY)
        if not data:
            return UserPreferences()
        return UserPreferences.from_dict(data)
    
    def update_preferences(self, **kwargs) -> UserPreferences:
        """更新用户偏好（部分更新）"""
        current = self.get_preferences()
        current_dict = current.to_dict()
        current_dict.update(kwargs)
        new_prefs = UserPreferences.from_dict(current_dict)
        self.db.set_preference(self.PREFERENCE_KEY, new_prefs.to_dict())
        return new_prefs
    
    def reset_to_defaults(self) -> UserPreferences:
        """重置为默认偏好"""
        defaults = UserPreferences()
        self.db.set_preference(self.PREFERENCE_KEY, defaults.to_dict())
        return defaults
    
    def get_interference_settings(self) -> dict:
        """获取干涉相关设置"""
        prefs = self.get_preferences()
        return {
            "enabled": prefs.interference_enabled,
            "intensity": prefs.interference_intensity,
            "domains": prefs.interference_domains,
            "mode": prefs.interference_mode,
        }
    
    def set_interference(
        self,
        enabled: bool = None,
        intensity: float = None,
        domains: list = None,
        mode: str = None,
    ) -> UserPreferences:
        """便捷设置干涉参数"""
        updates = {}
        if enabled is not None:
            updates["interference_enabled"] = enabled
        if intensity is not None:
            updates["interference_intensity"] = max(0.0, min(1.0, intensity))
        if domains is not None:
            updates["interference_domains"] = domains
        if mode is not None:
            if mode in ("on_request", "on_pattern", "on_conclusion"):
                updates["interference_mode"] = mode
        return self.update_preferences(**updates)
    
    def get_commitment_settings(self) -> dict:
        """获取承诺装置设置"""
        prefs = self.get_preferences()
        return {
            "lock_strength": prefs.commitment_lock_strength,
            "cooldown_hours": prefs.exit_cooldown_hours,
            "trusted_contact": prefs.trusted_contact,
        }