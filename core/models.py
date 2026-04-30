"""认知实验室 - 核心数据模型

设计约束（来自六位分析）:
- R1 (小马): 认知基模必须结构化、可查询、支持图遍历
- R2 (小哲): 推理链必须记录"即将闭合的节点"以触发中断
- R6 (小物): 模拟案例必须支持多模型并行对比和结果回溯
- R5 (小蛇): 不使用"盲区""错误"等规训性标签，只用"差异"和"对比"
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional
import uuid


class SchemaDomain(Enum):
    PROFESSIONAL = "professional"
    RELATIONAL = "relational"
    SELF_IDENTITY = "self_identity"
    LEARNING = "learning"
    WORLDVIEW = "worldview"
    TECHNICAL = "technical"
    UNCATEGORIZED = "uncategorized"


class SchemaConfidence(Enum):
    UNQUESTIONED = "unquestioned"
    EXAMINED = "examined"
    TENTATIVE = "tentative"
    REVISED = "revised"
    ABANDONED = "abandoned"


@dataclass
class CognitiveSchema:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    label: str = ""
    description: str = ""
    domain: SchemaDomain = SchemaDomain.UNCATEGORIZED
    confidence: SchemaConfidence = SchemaConfidence.UNQUESTIONED
    activation_count: int = 0
    last_activated: Optional[datetime] = None
    first_observed: datetime = field(default_factory=datetime.now)
    successful_applications: int = 0
    unsuccessful_applications: int = 0
    notes: str = ""

    def effectiveness_ratio(self) -> Optional[float]:
        total = self.successful_applications + self.unsuccessful_applications
        return self.successful_applications / total if total > 0 else None

    def to_dict(self) -> dict:
        return {
            "id": self.id, "label": self.label, "description": self.description,
            "domain": self.domain.value, "confidence": self.confidence.value,
            "activation_count": self.activation_count,
            "last_activated": self.last_activated.isoformat() if self.last_activated else None,
            "first_observed": self.first_observed.isoformat(),
            "successful_applications": self.successful_applications,
            "unsuccessful_applications": self.unsuccessful_applications, "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CognitiveSchema":
        return cls(
            id=data.get("id", str(uuid.uuid4())), label=data.get("label", ""),
            description=data.get("description", ""),
            domain=SchemaDomain(data.get("domain", "uncategorized")),
            confidence=SchemaConfidence(data.get("confidence", "unquestioned")),
            activation_count=data.get("activation_count", 0),
            last_activated=datetime.fromisoformat(data["last_activated"]) if data.get("last_activated") else None,
            first_observed=datetime.fromisoformat(data["first_observed"]) if data.get("first_observed") else datetime.now(),
            successful_applications=data.get("successful_applications", 0),
            unsuccessful_applications=data.get("unsuccessful_applications", 0),
            notes=data.get("notes", ""),
        )


@dataclass
class SchemaEdge:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source_id: str = ""
    target_id: str = ""
    relation_type: str = "supports"
    strength: float = 1.0
    evidence: str = ""

    def to_dict(self) -> dict:
        return {"id": self.id, "source_id": self.source_id, "target_id": self.target_id,
                "relation_type": self.relation_type, "strength": self.strength, "evidence": self.evidence}


@dataclass
class ReasoningStep:
    step_index: int = 0
    content: str = ""
    activated_schema_ids: list = field(default_factory=list)
    is_conclusion: bool = False
    would_have_benefited_from_interrupt: bool = False

    def to_dict(self) -> dict:
        return {"step_index": self.step_index, "content": self.content,
                "activated_schema_ids": self.activated_schema_ids,
                "is_conclusion": self.is_conclusion,
                "would_have_benefited_from_interrupt": self.would_have_benefited_from_interrupt}


@dataclass
class ReasoningChain:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str = ""
    topic: str = ""
    steps: list = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)
    outcome_satisfaction: Optional[bool] = None
    reflection: str = ""

    def to_dict(self) -> dict:
        return {"id": self.id, "session_id": self.session_id, "topic": self.topic,
                "steps": [s.to_dict() if hasattr(s, 'to_dict') else s for s in self.steps],
                "timestamp": self.timestamp.isoformat(),
                "outcome_satisfaction": self.outcome_satisfaction, "reflection": self.reflection}


@dataclass
class SimulationCase:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    problem_statement: str = ""
    domain: SchemaDomain = SchemaDomain.UNCATEGORIZED
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        return {"id": self.id, "problem_statement": self.problem_statement,
                "domain": self.domain.value, "created_at": self.created_at.isoformat()}


@dataclass
class SimulationRun:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    case_id: str = ""
    model_label: str = ""
    schema_ids_used: list = field(default_factory=list)
    predicted_outcome: str = ""
    predicted_confidence: float = 0.5
    run_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        return {"id": self.id, "case_id": self.case_id, "model_label": self.model_label,
                "schema_ids_used": self.schema_ids_used, "predicted_outcome": self.predicted_outcome,
                "predicted_confidence": self.predicted_confidence, "run_at": self.run_at.isoformat()}


@dataclass
class SimulationOutcome:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    run_id: str = ""
    actual_outcome: str = ""
    prediction_accuracy: Optional[float] = None
    what_was_missed: str = ""
    recorded_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        return {"id": self.id, "run_id": self.run_id, "actual_outcome": self.actual_outcome,
                "prediction_accuracy": self.prediction_accuracy, "what_was_missed": self.what_was_missed,
                "recorded_at": self.recorded_at.isoformat()}


@dataclass
class UserPreferences:
    interference_enabled: bool = False
    interference_intensity: float = 0.3
    interference_domains: list = field(default_factory=list)
    interference_mode: str = "on_request"
    commitment_lock_strength: str = "light"
    exit_cooldown_hours: int = 0
    trusted_contact: str = ""
    preferred_language_style: str = "auto"
    data_retention_days: int = 365
    export_format: str = "json"
    lab_mode_enabled: bool = True
    simulation_parallel_count: int = 3

    def __post_init__(self):
        if not self.interference_domains:
            self.interference_domains = ["professional"]

    def to_dict(self) -> dict:
        return {"interference_enabled": self.interference_enabled,
                "interference_intensity": self.interference_intensity,
                "interference_domains": self.interference_domains,
                "interference_mode": self.interference_mode,
                "commitment_lock_strength": self.commitment_lock_strength,
                "exit_cooldown_hours": self.exit_cooldown_hours,
                "trusted_contact": self.trusted_contact,
                "preferred_language_style": self.preferred_language_style,
                "data_retention_days": self.data_retention_days,
                "export_format": self.export_format,
                "lab_mode_enabled": self.lab_mode_enabled,
                "simulation_parallel_count": self.simulation_parallel_count}

    @classmethod
    def from_dict(cls, data: dict) -> "UserPreferences":
        return cls(
            interference_enabled=data.get("interference_enabled", False),
            interference_intensity=data.get("interference_intensity", 0.3),
            interference_domains=data.get("interference_domains", ["professional"]),
            interference_mode=data.get("interference_mode", "on_request"),
            commitment_lock_strength=data.get("commitment_lock_strength", "light"),
            exit_cooldown_hours=data.get("exit_cooldown_hours", 0),
            trusted_contact=data.get("trusted_contact", ""),
            preferred_language_style=data.get("preferred_language_style", "auto"),
            data_retention_days=data.get("data_retention_days", 365),
            export_format=data.get("export_format", "json"),
            lab_mode_enabled=data.get("lab_mode_enabled", True),
            simulation_parallel_count=data.get("simulation_parallel_count", 3))
