"""思维实验室核心引擎 — 小物 R6

只做差异对比，不做评判。选择权在你。
"""

from typing import Optional, List
from datetime import datetime
from .models import SimulationCase, SimulationRun, SimulationOutcome, SchemaDomain
from storage.database import Database


class SimulationEngine:
    def __init__(self, db: Database):
        self.db = db
    
    def create_case(self, problem: str, domain: SchemaDomain = SchemaDomain.UNCATEGORIZED) -> str:
        case = SimulationCase(problem_statement=problem, domain=domain)
        self.db.create_case({"id": case.id, "problem_statement": case.problem_statement,
                             "domain": case.domain.value, "created_at": case.created_at.isoformat()})
        return case.id
    
    def add_run(self, case_id: str, model_label: str, predicted_outcome: str,
                schema_ids_used: List[str] = None, confidence: float = 0.5) -> str:
        run = SimulationRun(case_id=case_id, model_label=model_label,
                            schema_ids_used=schema_ids_used or [],
                            predicted_outcome=predicted_outcome, predicted_confidence=confidence)
        self.db.create_run({"id": run.id, "case_id": run.case_id, "model_label": run.model_label,
                           "schema_ids_used": run.schema_ids_used, "predicted_outcome": run.predicted_outcome,
                           "predicted_confidence": run.predicted_confidence, "run_at": run.run_at.isoformat()})
        return run.id
    
    def record_actual_outcome(self, run_id: str, actual_outcome: str,
                              accuracy: Optional[float] = None, what_was_missed: str = "") -> str:
        outcome = SimulationOutcome(run_id=run_id, actual_outcome=actual_outcome,
                                    prediction_accuracy=accuracy, what_was_missed=what_was_missed)
        self.db.record_outcome({"id": outcome.id, "run_id": outcome.run_id, "actual_outcome": outcome.actual_outcome,
                               "prediction_accuracy": outcome.prediction_accuracy,
                               "what_was_missed": outcome.what_was_missed, "recorded_at": outcome.recorded_at.isoformat()})
        return outcome.id
    
    def get_comparison(self, case_id: str) -> Optional[str]:
        case = self.db.get_case_with_runs(case_id)
        if not case: return None
        lines = ["## 思维实验室：多模型对比\n", f"**问题**：{case['problem_statement']}\n"]
        if not case.get("runs"): lines.append("_尚未添加模型分析。_"); return "\n".join(lines)
        lines.append(f"**共 {len(case['runs'])} 个思维模型：**\n")
        for i, run in enumerate(case["runs"], 1):
            lines.append(f"### 模型 {i}：{run['model_label']}")
            lines.append(f"- 预测：{run['predicted_outcome']}")
            lines.append(f"- 信心度：{run['predicted_confidence']:.0%}")
            if run.get("schema_ids_used"):
                labels = [self.db.get_schema(sid)["label"] if self.db.get_schema(sid) else sid for sid in run["schema_ids_used"]]
                lines.append(f"- 框架：{', '.join(labels)}")
            if run.get("outcomes"):
                for o in run["outcomes"]:
                    lines.append(f"- **实际**：{o['actual_outcome']}")
            lines.append("")
        if len(case["runs"]) >= 2:
            lines.append("### 跨模型差异")
            for r in case["runs"]: lines.append(f"  - **{r['model_label']}**：{r['predicted_outcome']}")
            lines.append("\n_系统不判断哪个更好。选择权在你。_")
        return "\n".join(lines)
    
    def list_cases(self) -> List[dict]: return self.db.list_cases()
    def get_case_detail(self, case_id: str) -> Optional[dict]: return self.db.get_case_with_runs(case_id)