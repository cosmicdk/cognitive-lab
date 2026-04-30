"""推理模式检测器 — 小哲 R2

R5约束：不评判模式好坏，只标记与历史同构。
"""

from typing import Optional, List, Dict
from .models import ReasoningChain, ReasoningStep
from storage.database import Database


class PatternDetector:
    def __init__(self, db: Database):
        self.db = db
    
    def are_chains_isomorphic(self, chain_a: ReasoningChain, chain_b: ReasoningChain) -> bool:
        schemas_a, schemas_b = set(), set()
        for step in chain_a.steps:
            d = step.to_dict() if hasattr(step, 'to_dict') else step
            schemas_a.update(d.get("activated_schema_ids", []))
        for step in chain_b.steps:
            d = step.to_dict() if hasattr(step, 'to_dict') else step
            schemas_b.update(d.get("activated_schema_ids", []))
        if not schemas_a or not schemas_b: return False
        intersection = schemas_a & schemas_b
        return len(intersection) >= 2 and len(intersection) / min(len(schemas_a), len(schemas_b)) > 0.5
    
    def find_similar_chains(self, chain: ReasoningChain, limit: int = 20) -> List[Dict]:
        recent = self.db.get_recent_chains(limit=limit)
        similar = []
        for pc in recent:
            if pc["id"] == chain.id: continue
            pc_obj = ReasoningChain(id=pc["id"], session_id=pc.get("session_id", ""),
                                     topic=pc.get("topic", ""), steps=[ReasoningStep(**s) for s in pc.get("steps", [])])
            if self.are_chains_isomorphic(chain, pc_obj):
                similar.append({"chain_id": pc["id"], "topic": pc.get("topic", ""),
                                "timestamp": pc.get("timestamp", ""), "outcome_satisfaction": pc.get("outcome_satisfaction")})
        return similar
    
    def detect_closure_point(self, chain: ReasoningChain) -> Optional[int]:
        steps = chain.steps
        if len(steps) < 2: return None
        for i in range(len(steps) - 2, -1, -1):
            d = steps[i].to_dict() if hasattr(steps[i], 'to_dict') else steps[i]
            if not d.get("is_conclusion", False): return i
        return None
    
    def should_interrupt(self, chain: ReasoningChain, similar_chains: List[Dict],
                          interference_intensity: float, interference_mode: str) -> bool:
        if interference_mode == "on_request": return False
        if interference_mode == "on_conclusion":
            if self.detect_closure_point(chain) is not None and interference_intensity > 0.5: return True
        if interference_mode == "on_pattern" and similar_chains and len(similar_chains) >= 2:
            bad = sum(1 for c in similar_chains if c.get("outcome_satisfaction") is False)
            threshold = 0.7 - (bad / len(similar_chains) * 0.3)
            if interference_intensity >= threshold: return True
        return False
    
    def generate_interrupt_message(self, chain: ReasoningChain, similar_chains: List[Dict]) -> str:
        if not similar_chains: return ""
        topics = "、".join(c["topic"] for c in similar_chains[:3])
        bad = sum(1 for c in similar_chains if c.get("outcome_satisfaction") is False)
        good = sum(1 for c in similar_chains if c.get("outcome_satisfaction") is True)
        msg = f"💡 **认知模式识别**\n\n你当前的推理结构与此前 {len(similar_chains)} 次推理高度相似（{topics}）。\n\n"
        if bad > good: msg += f"{bad} 次结果未达预期。这次有什么不同吗？\n"
        elif good > bad: msg += f"{good} 次达到预期。这次是否适用相同框架？\n"
        else: msg += "结果好坏参半。\n"
        msg += "_只是模式识别，不是评判。你想：1.继续 2.换个框架 3.回顾上次_"
        return msg