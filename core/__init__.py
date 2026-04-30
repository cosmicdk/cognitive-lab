"""Core modules — v0.2.0

- models: Data models
- schema_tracker: Cognitive schema tracker
- pattern_detector: Reasoning pattern detector
- simulation_engine: Mental simulation lab
- interference: Real-time intervention engine
- translation: Cognitive language adapter
- analyzer: Automatic text analysis engine (NEW v0.2.0)
- session: Session manager (NEW v0.2.0)
"""

from .models import (
    CognitiveSchema, SchemaEdge, SchemaDomain, SchemaConfidence,
    ReasoningChain, ReasoningStep, SimulationCase, SimulationRun,
    SimulationOutcome, UserPreferences,
)
from .schema_tracker import SchemaTracker
from .simulation_engine import SimulationEngine
from .pattern_detector import PatternDetector
from .interference import InterferenceEngine
from .translation import TranslationEngine
from .analyzer import CognitiveAnalyzer, AnalysisResult, FissureType
from .session import Session, SessionStats

__all__ = [
    "CognitiveSchema", "SchemaEdge", "SchemaDomain", "SchemaConfidence",
    "ReasoningChain", "ReasoningStep", "SimulationCase", "SimulationRun",
    "SimulationOutcome", "UserPreferences",
    "SchemaTracker", "SimulationEngine", "PatternDetector",
    "InterferenceEngine", "TranslationEngine",
    "CognitiveAnalyzer", "AnalysisResult", "FissureType",
    "Session", "SessionStats",
]