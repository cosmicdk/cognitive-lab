"""认知变化报告生成器"""

import json
from datetime import datetime, timedelta
from typing import Optional
from storage.database import Database
from core.schema_tracker import SchemaTracker
from core.simulation_engine import SimulationEngine
from core.translation import TranslationEngine


class Reporter:
    def __init__(self, db: Database, translation: TranslationEngine = None):
        self.db = db
        self.tracker = SchemaTracker(db)
        self.engine = SimulationEngine(db)
        self.translation = translation or TranslationEngine(style="auto")
    
    def generate_full_report(self, since: datetime = None) -> str:
        if since is None: since = datetime.now() - timedelta(days=30)
        sections = [self._schema_overview(), self._reasoning_patterns(), self._lab_results(),
                     self.tracker.generate_change_summary(since)]
        return "\n\n".join(sections)
    
    def _schema_overview(self) -> str:
        schemas = self.db.get_all_schemas()
        if not schemas: return "## 认知基模概览\n\n尚未记录任何思维框架。"
        lines = [f"## 认知基模概览\n\n共记录 {len(schemas)} 个思维框架。\n"]
        active = [s for s in schemas if s.get("activation_count", 0) > 0]
        if active:
            lines.append(f"**活跃框架** ({len(active)} 个)：")
            for s in active:
                eff = ""
                total = s.get("successful_applications", 0) + s.get("unsuccessful_applications", 0)
                if total > 0: eff = f" 有效比 {s['successful_applications']/total:.0%}"
                lines.append(f"- {s['label']}（激活 {s['activation_count']} 次）{eff}")
        return "\n".join(lines)
    
    def _reasoning_patterns(self) -> str:
        chains = self.db.get_recent_chains(limit=20)
        if not chains: return "## 推理模式\n\n尚未记录任何推理链。"
        lines = [f"## 推理模式\n\n最近记录了 {len(chains)} 条推理链。\n"]
        patterns = self.tracker.find_similar_activation_patterns(10)
        if patterns: lines.append(f"\n检测到 {len(patterns)} 个重复模式。")
        return "\n".join(lines)
    
    def _lab_results(self) -> str:
        cases = self.engine.list_cases()
        if not cases: return "## 思维实验室\n\n尚未创建任何模拟案例。"
        lines = [f"## 思维实验室\n\n共 {len(cases)} 个模拟案例。\n"]
        done = sum(1 for c in cases if any(r.get("outcomes") for r in self.engine.get_case_detail(c["id"]).get("runs", [])) if self.engine.get_case_detail(c["id"]))
        lines.append(f"其中 {done} 个已记录实际结果。")
        return "\n".join(lines)
    
    def generate_json_report(self, since: datetime = None) -> dict:
        if since is None: since = datetime.now() - timedelta(days=30)
        return {"schemas": self.db.get_all_schemas(), "chains": self.db.get_recent_chains(limit=50),
                "patterns": self.tracker.find_similar_activation_patterns(),
                "cases": [self.engine.get_case_detail(c["id"]) for c in self.engine.list_cases()],
                "generated_at": datetime.now().isoformat(), "period": since.isoformat()}
    
    def export_report(self, filepath: str, format: str = "txt"):
        if format == "json":
            with open(filepath, "w", encoding="utf-8") as f: json.dump(self.generate_json_report(), f, ensure_ascii=False, indent=2)
        elif format == "md":
            with open(filepath, "w", encoding="utf-8") as f: f.write(self.generate_full_report())
        else:
            with open(filepath, "w", encoding="utf-8") as f: f.write(self.generate_full_report())
        return filepath