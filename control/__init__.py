"""Cognitive Lab - 控制层

用户完全控制：
- preferences: 用户偏好管理
- commitment: 承诺装置
"""

from .preferences import PreferenceManager
from .commitment import CommitmentDevice

__all__ = ["PreferenceManager", "CommitmentDevice"]