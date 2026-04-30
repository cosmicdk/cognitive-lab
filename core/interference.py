"""干涉决策引擎 — 小哲 R2 + 小参 R3

默认关闭主动干涉。用户完全控制。
"""

from typing import Optional, List
from .models import ReasoningChain, UserPreferences, SchemaDomain
from .pattern_detector import PatternDetector
from storage.database import Database


class InterferenceEngine:
    def __init__(self, db: Database, preferences: UserPreferences):
        self.db = db
        self.preferences = preferences
        self.detector = PatternDetector(db)
        self._intervention_history: List[dict] = []
    
    def analyze_and_decide(self, chain: ReasoningChain, domain: SchemaDomain = SchemaDomain.UNCATEGORIZED) -> Optional[str]:
        if not self.preferences.interference_enabled: return None
        if domain.value not in self.preferences.interference_domains: return None
        similar = self.detector.find_similar_chains(chain)
        should = self.detector.should_interrupt(chain=chain, similar_chains=similar,
            interference_intensity=self.preferences.interference_intensity,
            interference_mode=self.preferences.interference_mode)
        if not should: return None
        msg = self.detector.generate_interrupt_message(chain, similar)
        if not msg: return None
        msg = self._adapt_language_style(msg)
        self._intervention_history.append({"chain_id": chain.id, "topic": chain.topic,
            "similar_count": len(similar),
            "timestamp": chain.timestamp.isoformat() if hasattr(chain.timestamp, 'isoformat') else str(chain.timestamp)})
        return msg
    
    def _adapt_language_style(self, message: str) -> str:
        style = self.preferences.preferred_language_style
        if style == "conceptual": return message
        elif style == "experiential": return "根据你过往的思维记录——\n\n" + message
        elif style == "analogical": return message + "\n\n_就像走路——如果每次都走到同一个死胡同，也许可以试试拐个弯。_"
        return message
    
    def get_intervention_summary(self) -> dict:
        if not self._intervention_history: return {"total_interventions": 0, "recent": []}
        return {"total_interventions": len(self._intervention_history), "recent": self._intervention_history[-5:]}
    
    def update_preferences(self, new_prefs: UserPreferences):
        self.preferences = new_prefs