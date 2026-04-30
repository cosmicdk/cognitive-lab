"""Session manager — v0.2.0 real-time tracking

Manages real-time conversation/thinking sessions:
1. Accumulate session context (short-term memory)
2. Track temporal changes in schema activations
3. Manage intervention cooldown
4. Generate session-level insights
"""

import time
from typing import Optional, List, Dict
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from .analyzer import AnalysisResult, CognitiveFissure, FissureType


@dataclass
class SessionStats:
    total_messages: int = 0
    total_schema_activations: int = 0
    total_fissures: int = 0
    dominant_schema: str = ""
    dominant_domain: str = ""
    certainty_trend: List[float] = field(default_factory=list)
    openness_trend: List[float] = field(default_factory=list)
    fissure_counts: Dict[str, int] = field(default_factory=dict)


class Session:
    DEFAULT_IDLE_TIMEOUT = 30 * 60
    INTERVENTION_COOLDOWN = 5

    def __init__(self, session_id: str = None):
        self.session_id = session_id or f"session-{int(time.time())}"
        self.created_at = datetime.now()
        self.last_activity = datetime.now()
        self.results: List[AnalysisResult] = []
        self.interventions: List[dict] = []
        self._last_intervention_index: int = -100
        self._schema_activation_counter: Dict[str, int] = {}

    def add_result(self, result: AnalysisResult) -> None:
        self.results.append(result)
        self.last_activity = datetime.now()
        for match in result.matched_schemas:
            label = match.label
            self._schema_activation_counter[label] = self._schema_activation_counter.get(label, 0) + 1

    def is_idle(self, timeout: int = None) -> bool:
        timeout = timeout or self.DEFAULT_IDLE_TIMEOUT
        elapsed = (datetime.now() - self.last_activity).total_seconds()
        return elapsed > timeout

    def can_intervene(self) -> bool:
        if not self.results:
            return False
        messages_since_last = len(self.results) - self._last_intervention_index
        return messages_since_last >= self.INTERVENTION_COOLDOWN

    def record_intervention(self, intervention: dict) -> None:
        self.interventions.append(intervention)
        self._last_intervention_index = len(self.results)

    def get_stats(self) -> SessionStats:
        stats = SessionStats()
        stats.total_messages = len(self.results)
        for r in self.results:
            stats.total_schema_activations += len(r.matched_schemas)
            stats.total_fissures += len(r.fissures)
            stats.certainty_trend.append(r.linguistic.certainty_score)
            stats.openness_trend.append(r.linguistic.openness_score)
            for f in r.fissures:
                ftype = f.type.value
                stats.fissure_counts[ftype] = stats.fissure_counts.get(ftype, 0) + 1
        if self._schema_activation_counter:
            stats.dominant_schema = max(self._schema_activation_counter, key=self._schema_activation_counter.get)
        domain_counter: Dict[str, int] = {}
        for r in self.results:
            domain_counter[r.domain] = domain_counter.get(r.domain, 0) + 1
        if domain_counter:
            stats.dominant_domain = max(domain_counter, key=domain_counter.get)
        return stats

    def get_recent_context(self, n: int = 5) -> List[str]:
        return [r.text for r in self.results[-n:]]

    def should_generate_session_report(self) -> bool:
        return len(self.results) >= 10 or len(self.interventions) >= 2

    def generate_session_summary(self) -> str:
        stats = self.get_stats()
        lines = [f"## Session {self.session_id[:8]} Summary\n"]
        lines.append(f"Duration: {(datetime.now() - self.created_at).total_seconds() / 60:.0f} min")
        lines.append(f"Messages: {stats.total_messages}")
        lines.append(f"Schema activations: {stats.total_schema_activations}")
        lines.append(f"Cognitive fissures: {stats.total_fissures}")
        if stats.dominant_schema:
            lines.append(f"Dominant schema: {stats.dominant_schema}")
        if stats.fissure_counts:
            lines.append("\nFissure distribution:")
            for ftype, count in sorted(stats.fissure_counts.items(), key=lambda x: -x[1]):
                lines.append(f"  - {ftype}: {count}")
        if self.interventions:
            lines.append(f"\nInterventions: {len(self.interventions)}")
            for i, iv in enumerate(self.interventions[-3:], 1):
                lines.append(f"  {i}. {iv.get('reason', '')[:60]}")
        if stats.certainty_trend and len(stats.certainty_trend) >= 5:
            recent_cert = sum(stats.certainty_trend[-5:]) / 5
            early_cert = sum(stats.certainty_trend[:5]) / 5 if len(stats.certainty_trend) >= 5 else recent_cert
            if recent_cert > early_cert * 1.3:
                lines.append("\nWarning: thinking rigidity trending up")
            elif recent_cert < early_cert * 0.7:
                lines.append("\nGood: thinking openness improving")
        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "created_at": self.created_at.isoformat(),
            "message_count": len(self.results),
            "intervention_count": len(self.interventions),
            "stats": {
                "certainty_trend": self.get_stats().certainty_trend[-20:],
                "openness_trend": self.get_stats().openness_trend[-20:],
                "dominant_schema": self.get_stats().dominant_schema,
            },
        }