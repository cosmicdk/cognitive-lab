"""Cognitive Lab - 核心模块

功能模块：
- models: 数据模型定义
- schema_tracker: 认知基模追踪器（小马 R1）
- pattern_detector: 推理模式检测器（小哲 R2）
- simulation_engine: 思维实验室引擎（小物 R6）
- interference: 干涉决策引擎（小参 R3）
- translation: 认知母语适配层（小蛇 R5）
"""

from .models import (
    CognitiveSchema,
    SchemaEdge,
    SchemaDomain,
    SchemaConfidence,
    ReasoningChain,
    ReasoningStep,
    SimulationCase,
    SimulationRun,
    SimulationOutcome,
    UserPreferences,
)
from .schema_tracker import SchemaTracker
from .simulation_engine import SimulationEngine
from .pattern_detector import PatternDetector
from .interference import InterferenceEngine
from .translation import TranslationEngine

__all__ = [
    # 数据模型
    "CognitiveSchema",
    "SchemaEdge",
    "SchemaDomain",
    "SchemaConfidence",
    "ReasoningChain",
    "ReasoningStep",
    "SimulationCase",
    "SimulationRun",
    "SimulationOutcome",
    "UserPreferences",
    # 引擎
    "SchemaTracker",
    "SimulationEngine",
    "PatternDetector",
    "InterferenceEngine",
    "TranslationEngine",
]