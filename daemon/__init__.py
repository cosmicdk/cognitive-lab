"""Daemon package — v0.2.0

Background cognitive monitoring & intervention system.
"""

from .watcher import DaemonWatcher
from .pipeline import AnalysisPipeline
from .feedback import FeedbackLoop

__all__ = ["DaemonWatcher", "AnalysisPipeline", "FeedbackLoop"]