"""认知基模追踪器 — 小马"认知镜像层"的最小实现

功能：
1. 从推理链中提取激活的基模
2. 维护基模之间的支撑/依赖关系
3. 检测基模重复激活模式

R5 小蛇约束：只做"对比"，不做评判
"""

from typing import Optional, List
from datetime import datetime, timedelta
from collections import Counter
from .models import (
    CognitiveSchema, SchemaEdge, SchemaDomain, SchemaConfidence,
    ReasoningChain, ReasoningStep
)
from storage.database import Database


class SchemaTracker:
    def __init__(self, db: Database):
        self.db = db
    
    def extract_schemas_from_chain(self, chain: ReasoningChain) -> List[str]:
        activated_ids = []
        for step in chain.steps:
            step_data = step.to_dict() if hasattr(step, 'to_dict') else step
            for sid in step_data.get("activated_schema_ids", []):
                if sid not in activated_ids:
                    activated_ids.append(sid)
                    schema = self.db.get_schema(sid)
                    if schema: self.db.increment_activation(sid)
        return activated_ids
    
    def register_schema(self, label: str, description: str, domain: SchemaDomain = SchemaDomain.UNCATEGORIZED,
                        confidence: SchemaConfidence = SchemaConfidence.TENTATIVE, depends_on: List[str] = None) -> str:
        existing = self.db.get_all_schemas()
        for s in existing:
            if s["label"].strip().lower() == label.strip().lower(): return s["id"]
        schema = CognitiveSchema(label=label, description=description, domain=domain, confidence=confidence)
        schema_id = self.db.upsert_schema({"id": schema.id, "label": schema.label, "description": schema.description,
            "domain": schema.domain.value, "confidence": schema.confidence.value,
            "activation_count": 1, "last_activated": datetime.now().isoformat(),
            "first_observed": schema.first_observed.isoformat(),
            "successful_applications": 0, "unsuccessful_applications": 0, "notes": ""})
        if depends_on:
            for dep_id in depends_on:
                edge = SchemaEdge(source_id=schema_id, target_id=dep_id, relation_type="supports", evidence="用户注册时指定")
                self.db.add_edge(edge.to_dict())
        return schema_id
    
    def get_schema_graph(self) -> dict:
        return self.db.get_schema_graph()
    
    def find_deepest_dependencies(self, schema_id: str, max_depth: int = 5) -> List[str]:
        visited = set()
        frontier = [schema_id]
        deepest = []
        for _ in range(max_depth):
            next_frontier = []
            for sid in frontier:
                if sid in visited: continue
                visited.add(sid)
                edges = self.db.get_edges_for_schema(sid)
                deps = [e["target_id"] for e in edges if e["source_id"] == sid and e["relation_type"] == "supports"]
                if deps: next_frontier.extend(deps)
                elif sid not in deepest: deepest.append(sid)
            if not next_frontier: break
            frontier = next_frontier
        return deepest
    
    def find_similar_activation_patterns(self, recent_chains_count: int = 10) -> List[dict]:
        chains = self.db.get_recent_chains(limit=recent_chains_count)
        pattern_counter = Counter()
        pattern_to_chains = {}
        for chain in chains:
            schema_ids = []
            for step in chain.get("steps", []):
                for sid in step.get("activated_schema_ids", []):
                    if sid not in schema_ids: schema_ids.append(sid)
            pattern_key = frozenset(schema_ids)
            if not pattern_key: continue
            pattern_counter[pattern_key] += 1
            if pattern_key not in pattern_to_chains: pattern_to_chains[pattern_key] = []
            pattern_to_chains[pattern_key].append(chain["id"])
        results = []
        for pattern_key, count in pattern_counter.most_common():
            if count >= 2:
                schema_labels = [self.db.get_schema(sid)["label"] if self.db.get_schema(sid) else sid for sid in pattern_key]
                results.append({"schema_ids": list(pattern_key), "schema_labels": schema_labels,
                                "occurrence_count": count, "chain_ids": pattern_to_chains[pattern_key]})
        return results
    
    def generate_change_summary(self, since: datetime = None) -> str:
        if since is None: since = datetime.now() - timedelta(days=7)
        schemas = self.db.get_all_schemas()
        recent = [s for s in schemas if s.get("last_activated") and s["last_activated"] > since.isoformat()]
        dormant = [s for s in schemas if s.get("last_activated") and s["last_activated"] <= since.isoformat() and s["activation_count"] > 0]
        lines = [f"📊 认知基模变化摘要（{since.strftime('%Y-%m-%d')} 至今）\n"]
        if recent:
            lines.append("**近期活跃的思维框架：**")
            for s in sorted(recent, key=lambda x: x["activation_count"], reverse=True):
                ratio = ""
                total = s["successful_applications"] + s["unsuccessful_applications"]
                if total > 0: ratio = f" [有效比: {s['successful_applications']/total:.0%}]"
                lines.append(f"  • {s['label']}（激活 {s['activation_count']} 次）{ratio}")
        if dormant:
            lines.append("\n**近期未激活的框架：**")
            for s in dormant[:5]: lines.append(f"  • {s['label']}（上次使用: {s['last_activated'][:10]}）")
        patterns = self.find_similar_activation_patterns()
        if patterns:
            lines.append("\n**重复出现的推理模式：**")
            for p in patterns[:3]:
                labels = ", ".join(p["schema_labels"])
                lines.append(f"  • [{labels}] 出现了 {p['occurrence_count']} 次")
        return "\n".join(lines)
    
    def export_graph_json(self) -> dict:
        graph = self.get_schema_graph()
        return {
            "nodes": [{"id": n["id"], "label": n["label"], "group": n["domain"], "value": n["activation_count"]} for n in graph["nodes"]],
            "edges": [{"from": e["source_id"], "to": e["target_id"], "label": e["relation_type"], "value": e["strength"]} for e in graph["edges"]]
        }