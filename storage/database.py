"""认知实验室 - SQLite 存储层

设计原则：
- 本地文件数据库，用户完全拥有数据（小蛇 R5 公共品属性）
- 所有表支持完整 CRUD
- 迁移脚本内嵌，零外部依赖
"""

import sqlite3
import json
import os
from datetime import datetime
from typing import Optional, List
from pathlib import Path

DEFAULT_DB_PATH = os.path.expanduser("~/.cognitive-lab/data.db")


class Database:
    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA foreign_keys=ON")
        self._migrate()

    def _migrate(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS cognitive_schemas (
                id TEXT PRIMARY KEY, label TEXT NOT NULL, description TEXT DEFAULT '',
                domain TEXT DEFAULT 'uncategorized', confidence TEXT DEFAULT 'unquestioned',
                activation_count INTEGER DEFAULT 0, last_activated TEXT,
                first_observed TEXT NOT NULL, successful_applications INTEGER DEFAULT 0,
                unsuccessful_applications INTEGER DEFAULT 0, notes TEXT DEFAULT '');
            CREATE TABLE IF NOT EXISTS schema_edges (
                id TEXT PRIMARY KEY, source_id TEXT NOT NULL, target_id TEXT NOT NULL,
                relation_type TEXT DEFAULT 'supports', strength REAL DEFAULT 1.0, evidence TEXT DEFAULT '',
                FOREIGN KEY (source_id) REFERENCES cognitive_schemas(id) ON DELETE CASCADE,
                FOREIGN KEY (target_id) REFERENCES cognitive_schemas(id) ON DELETE CASCADE);
            CREATE TABLE IF NOT EXISTS reasoning_chains (
                id TEXT PRIMARY KEY, session_id TEXT NOT NULL, topic TEXT DEFAULT '',
                steps_json TEXT DEFAULT '[]', timestamp TEXT NOT NULL,
                outcome_satisfaction INTEGER, reflection TEXT DEFAULT '');
            CREATE TABLE IF NOT EXISTS simulation_cases (
                id TEXT PRIMARY KEY, problem_statement TEXT NOT NULL,
                domain TEXT DEFAULT 'uncategorized', created_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS simulation_runs (
                id TEXT PRIMARY KEY, case_id TEXT NOT NULL, model_label TEXT NOT NULL,
                schema_ids_json TEXT DEFAULT '[]', predicted_outcome TEXT DEFAULT '',
                predicted_confidence REAL DEFAULT 0.5, run_at TEXT NOT NULL,
                FOREIGN KEY (case_id) REFERENCES simulation_cases(id) ON DELETE CASCADE);
            CREATE TABLE IF NOT EXISTS simulation_outcomes (
                id TEXT PRIMARY KEY, run_id TEXT NOT NULL, actual_outcome TEXT DEFAULT '',
                prediction_accuracy REAL, what_was_missed TEXT DEFAULT '', recorded_at TEXT NOT NULL,
                FOREIGN KEY (run_id) REFERENCES simulation_runs(id) ON DELETE CASCADE);
            CREATE TABLE IF NOT EXISTS user_preferences (
                key TEXT PRIMARY KEY, value_json TEXT NOT NULL, updated_at TEXT NOT NULL);
            CREATE INDEX IF NOT EXISTS idx_schemas_domain ON cognitive_schemas(domain);
            CREATE INDEX IF NOT EXISTS idx_chains_session ON reasoning_chains(session_id);
            CREATE INDEX IF NOT EXISTS idx_runs_case ON simulation_runs(case_id);
        """)
        self.conn.commit()

    def upsert_schema(self, schema_dict: dict) -> str:
        cols = ", ".join(schema_dict.keys())
        placeholders = ", ".join("?" for _ in schema_dict)
        updates = ", ".join(f"{k}=excluded.{k}" for k in schema_dict if k != "id")
        sql = f"INSERT INTO cognitive_schemas ({cols}) VALUES ({placeholders}) ON CONFLICT(id) DO UPDATE SET {updates}"
        self.conn.execute(sql, list(schema_dict.values()))
        self.conn.commit()
        return schema_dict["id"]

    def get_schema(self, schema_id: str) -> Optional[dict]:
        row = self.conn.execute("SELECT * FROM cognitive_schemas WHERE id=?", (schema_id,)).fetchone()
        return dict(row) if row else None

    def get_all_schemas(self) -> List[dict]:
        rows = self.conn.execute("SELECT * FROM cognitive_schemas ORDER BY activation_count DESC").fetchall()
        return [dict(r) for r in rows]

    def increment_activation(self, schema_id: str) -> None:
        self.conn.execute("UPDATE cognitive_schemas SET activation_count=activation_count+1, last_activated=? WHERE id=?",
            (datetime.now().isoformat(), schema_id))
        self.conn.commit()

    def delete_schema(self, schema_id: str) -> bool:
        cursor = self.conn.execute("DELETE FROM cognitive_schemas WHERE id=?", (schema_id,))
        self.conn.commit()
        return cursor.rowcount > 0

    def add_edge(self, edge_dict: dict) -> str:
        cols = ", ".join(edge_dict.keys())
        placeholders = ", ".join("?" for _ in edge_dict)
        self.conn.execute(f"INSERT OR REPLACE INTO schema_edges ({cols}) VALUES ({placeholders})", list(edge_dict.values()))
        self.conn.commit()
        return edge_dict["id"]

    def get_edges_for_schema(self, schema_id: str) -> List[dict]:
        rows = self.conn.execute("SELECT * FROM schema_edges WHERE source_id=? OR target_id=?", (schema_id, schema_id)).fetchall()
        return [dict(r) for r in rows]

    def get_schema_graph(self) -> dict:
        nodes = self.get_all_schemas()
        edges = [dict(r) for r in self.conn.execute("SELECT * FROM schema_edges").fetchall()]
        return {"nodes": nodes, "edges": edges}

    def save_chain(self, chain_dict: dict) -> str:
        chain_dict = dict(chain_dict)
        chain_dict["steps_json"] = json.dumps(chain_dict.pop("steps", []), ensure_ascii=False)
        cols = ", ".join(chain_dict.keys())
        placeholders = ", ".join("?" for _ in chain_dict)
        self.conn.execute(f"INSERT INTO reasoning_chains ({cols}) VALUES ({placeholders})", list(chain_dict.values()))
        self.conn.commit()
        return chain_dict["id"]

    def get_recent_chains(self, limit: int = 20) -> List[dict]:
        rows = self.conn.execute("SELECT * FROM reasoning_chains ORDER BY timestamp DESC LIMIT ?", (limit,)).fetchall()
        results = []
        for r in rows:
            d = dict(r)
            d["steps"] = json.loads(d.pop("steps_json", "[]"))
            results.append(d)
        return results

    def create_case(self, case_dict: dict) -> str:
        cols = ", ".join(case_dict.keys())
        placeholders = ", ".join("?" for _ in case_dict)
        self.conn.execute(f"INSERT INTO simulation_cases ({cols}) VALUES ({placeholders})", list(case_dict.values()))
        self.conn.commit()
        return case_dict["id"]

    def get_case(self, case_id: str) -> Optional[dict]:
        row = self.conn.execute("SELECT * FROM simulation_cases WHERE id=?", (case_id,)).fetchone()
        return dict(row) if row else None

    def list_cases(self) -> List[dict]:
        rows = self.conn.execute("SELECT id, problem_statement, domain, created_at FROM simulation_cases ORDER BY created_at DESC").fetchall()
        return [dict(r) for r in rows]

    def create_run(self, run_dict: dict) -> str:
        run_dict = dict(run_dict)
        run_dict["schema_ids_json"] = json.dumps(run_dict.pop("schema_ids_used", []))
        cols = ", ".join(run_dict.keys())
        placeholders = ", ".join("?" for _ in run_dict)
        self.conn.execute(f"INSERT INTO simulation_runs ({cols}) VALUES ({placeholders})", list(run_dict.values()))
        self.conn.commit()
        return run_dict["id"]

    def get_runs_for_case(self, case_id: str) -> List[dict]:
        rows = self.conn.execute("SELECT * FROM simulation_runs WHERE case_id=? ORDER BY run_at", (case_id,)).fetchall()
        results = []
        for r in rows:
            d = dict(r)
            d["schema_ids_used"] = json.loads(d.pop("schema_ids_json", "[]"))
            results.append(d)
        return results

    def record_outcome(self, outcome_dict: dict) -> str:
        cols = ", ".join(outcome_dict.keys())
        placeholders = ", ".join("?" for _ in outcome_dict)
        self.conn.execute(f"INSERT INTO simulation_outcomes ({cols}) VALUES ({placeholders})", list(outcome_dict.values()))
        self.conn.commit()
        return outcome_dict["id"]

    def get_outcomes_for_run(self, run_id: str) -> List[dict]:
        rows = self.conn.execute("SELECT * FROM simulation_outcomes WHERE run_id=?", (run_id,)).fetchall()
        return [dict(r) for r in rows]

    def get_case_with_runs(self, case_id: str) -> Optional[dict]:
        case = self.get_case(case_id)
        if not case: return None
        runs = self.get_runs_for_case(case_id)
        for r in runs:
            r["outcomes"] = self.get_outcomes_for_run(r["id"])
        result = dict(case)
        result["runs"] = runs
        return result

    def set_preference(self, key: str, value: dict) -> None:
        self.conn.execute("INSERT OR REPLACE INTO user_preferences (key, value_json, updated_at) VALUES (?, ?, ?)",
            (key, json.dumps(value, ensure_ascii=False), datetime.now().isoformat()))
        self.conn.commit()

    def get_preference(self, key: str) -> Optional[dict]:
        row = self.conn.execute("SELECT value_json FROM user_preferences WHERE key=?", (key,)).fetchone()
        return json.loads(row["value_json"]) if row else None

    def export_all(self) -> dict:
        return {
            "schemas": self.get_all_schemas(),
            "edges": [dict(r) for r in self.conn.execute("SELECT * FROM schema_edges").fetchall()],
            "chains": self.get_recent_chains(limit=1000),
            "cases": [self.get_case_with_runs(c["id"]) for c in self.list_cases()],
            "preferences": {r["key"]: json.loads(r["value_json"]) for r in self.conn.execute("SELECT key, value_json FROM user_preferences").fetchall()},
            "exported_at": datetime.now().isoformat(),
        }

    def close(self):
        self.conn.close()
