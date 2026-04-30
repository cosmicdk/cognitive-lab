#!/usr/bin/env python3
"""認知實驗室 CLI — v0.2.0

用法：
  cognitive-lab schema list          # 列出所有認知基模
  cognitive-lab schema add            # 互動式添加基模
  cognitive-lab schema graph          # 導出認知基模圖
  cognitive-lab chain record          # 記錄一條推理鏈
  cognitive-lab chain recent          # 查看最近的推理鏈
  cognitive-lab sim create            # 創建思維實驗室案例
  cognitive-lab sim compare <case_id> # 多模型對比
  cognitive-lab sim outcome <run_id>  # 記錄實際結果
  cognitive-lab report                # 生成認知變化摘要
  cognitive-lab prefs show            # 查看當前偏好
  cognitive-lab prefs set             # 設置偏好
  cognitive-lab prefs reset           # 重置偏好
  cognitive-lab export                # 導出全部數據

  cognitive-lab daemon [--mode silent|monitor|active]  # 啟動後台守護
  cognitive-lab daemon --watch <file> [--mode active]  # 監聽文件
  cognitive-lab analyze <text>         # 一次性文本分析
  cognitive-lab analyze --stdin        # 從管道分析
  cognitive-lab feedback <case_id>     # 預測vs結果對比
  cognitive-lab growth [--days 30]     # 認知成長報告
  cognitive-lab status                 # 查看當前狀態
"""

import sys
import os
import json
from datetime import datetime

_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _project_root)

from storage.database import Database
from core.schema_tracker import SchemaTracker
from core.simulation_engine import SimulationEngine
from core.pattern_detector import PatternDetector
from core.models import SchemaDomain, SchemaConfidence, ReasoningChain, ReasoningStep
from control.preferences import PreferenceManager
from control.commitment import CommitmentDevice
from core.translation import TranslationEngine
from core.analyzer import CognitiveAnalyzer, quick_analyze
from core.session import Session


def get_translation_engine(db: Database) -> TranslationEngine:
    prefs = PreferenceManager(db).get_preferences()
    return TranslationEngine(style=prefs.preferred_language_style)


# ═══════════════════════════════════════════════
# Schema / Chain / Simulation / Report / Prefs / Export
# ═══════════════════════════════════════════════

def cmd_schema_list(args, db, tracker, **_):
    t = get_translation_engine(db)
    schemas = db.get_all_schemas()
    if not schemas:
        print("還沒有記錄任何思維框架。使用 `schema add` 添加第一個。")
        return
    print(f"\n📊 {t.translate('schema')} 地圖（共 {len(schemas)} 個節點）\n")
    icons = {"unquestioned": "⚪", "examined": "🔍", "tentative": "🌱", "revised": "🔄", "abandoned": "💤"}
    for s in schemas:
        icon = icons.get(s.get("confidence", ""), "❓")
        print(f"  {icon} [{s.get('domain', '')}] {s['label']}")
        total = s.get("successful_applications", 0) + s.get("unsuccessful_applications", 0)
        eff = f"有效比: {s['successful_applications']/total:.0%}" if total > 0 else "有效比: 暫無數據"
        print(f"     激活 {s.get('activation_count', 0)} 次 | {eff}")
        if s.get("description"):
            print(f"     {s['description'][:80]}")
        print()


def cmd_schema_add(args, db, tracker, **_):
    print("\n🆕 添加新的思維框架\n")
    label = input("名稱（簡短標籤）：").strip()
    if not label: print("已取消。"); return
    description = input("詳細描述：").strip()
    print("\n領域：professional / relational / self_identity / learning / worldview / technical")
    domain_input = input("選擇（直接回車=uncategorized）：").strip()
    try: domain = SchemaDomain(domain_input) if domain_input else SchemaDomain.UNCATEGORIZED
    except ValueError: domain = SchemaDomain.UNCATEGORIZED
    print("\n確信程度：unquestioned / examined / tentative / revised / abandoned")
    conf_input = input("選擇（直接回車=tentative）：").strip()
    try: confidence = SchemaConfidence(conf_input) if conf_input else SchemaConfidence.TENTATIVE
    except ValueError: confidence = SchemaConfidence.TENTATIVE
    sid = tracker.register_schema(label=label, description=description, domain=domain, confidence=confidence)
    print(f"\n✅ 框架已註冊，ID: {sid[:8]}...")


def cmd_schema_graph(args, db, tracker, **_):
    print(json.dumps(tracker.export_graph_json(), ensure_ascii=False, indent=2))


def cmd_chain_record(args, db, tracker, **_):
    print("\n📝 記錄推理鏈\n")
    topic = input("推理主題：").strip()
    if not topic: print("已取消。"); return
    steps = []
    print("輸入推理步驟（空行結束）：")
    i = 1
    while True:
        content = input(f"  步驟 {i}：").strip()
        if not content: break
        is_conclusion = input(f"  最終結論？(y/n)：").strip().lower() == "y"
        steps.append(ReasoningStep(step_index=i, content=content, activated_schema_ids=[], is_conclusion=is_conclusion))
        i += 1
    if not steps: print("沒有輸入任何步驟。"); return
    schemas = db.get_all_schemas()
    print("\n🔗 自動匹配已有思維框架...")
    for step in steps:
        for s in schemas:
            if any(kw in step.content.lower() for kw in s["label"].lower().split()):
                step.activated_schema_ids.append(s["id"])
                print(f"  步驟 {step.step_index} → {s['label']}")
    chain = ReasoningChain(session_id=f"cli-{datetime.now().strftime('%Y%m%d-%H%M%S')}", topic=topic, steps=steps)
    db.save_chain(chain.to_dict())
    for step in steps:
        for sid in step.activated_schema_ids:
            db.increment_activation(sid)
    print(f"\n✅ 推理鏈已保存，ID: {chain.id[:8]}...")


def cmd_chain_recent(args, db, tracker, **_):
    chains = db.get_recent_chains(limit=10)
    if not chains: print("還沒有任何推理鏈記錄。"); return
    print(f"\n📋 最近 {len(chains)} 條推理鏈：\n")
    for c in chains:
        sat = "😊" if c.get("outcome_satisfaction") else ("😞" if c.get("outcome_satisfaction") is False else "❓")
        print(f"  {sat} [{c['id'][:8]}] {c['topic']}")
        print(f"     {c['timestamp'][:19]} | {len(c.get('steps', []))} 步\n")


def cmd_sim_create(args, db, tracker, engine, **_):
    print("\n🧪 創建思維實驗室案例\n")
    problem = input("描述問題：").strip()
    if not problem: print("已取消。"); return
    print("\n領域：professional / relational / self_identity / learning / worldview / technical")
    domain_input = input("選擇：").strip()
    try: domain = SchemaDomain(domain_input) if domain_input else SchemaDomain.UNCATEGORIZED
    except ValueError: domain = SchemaDomain.UNCATEGORIZED
    case_id = engine.create_case(problem, domain)
    print(f"\n✅ 案例已創建，ID: {case_id[:8]}...")


def cmd_sim_add_run(args, db, tracker, engine, **_):
    if len(args) < 1: print("用法: sim add-run <case_id>"); return
    cases = engine.list_cases()
    case = next((c for c in cases if c["id"].startswith(args[0])), None)
    if not case: print(f"未找到: {args[0]}"); return
    print(f"\n案例：{case['problem_statement'][:80]}")
    model_label = input("模型名稱：").strip()
    predicted = input("預測結果：").strip()
    conf_str = input("信心度 (0.0~1.0)：").strip()
    confidence = float(conf_str) if conf_str else 0.5
    engine.add_run(case_id=case["id"], model_label=model_label, predicted_outcome=predicted, confidence=confidence)
    print("✅ 運行已添加。")


def cmd_sim_compare(args, db, tracker, engine, **_):
    if len(args) < 1: print("用法: sim compare <case_id>"); return
    cases = engine.list_cases()
    case = next((c for c in cases if c["id"].startswith(args[0])), None)
    if not case: print(f"未找到: {args[0]}"); return
    print("\n" + engine.get_comparison(case["id"]))


def cmd_sim_list(args, db, tracker, engine, **_):
    cases = engine.list_cases()
    if not cases: print("還沒有案例。"); return
    print(f"\n🧪 思維實驗室案例（共 {len(cases)} 個）：\n")
    for c in cases:
        print(f"  📋 [{c['id'][:8]}] {c['problem_statement'][:60]}")
        print(f"     {c['domain']} | {c['created_at'][:19]}\n")


def cmd_sim_outcome(args, db, tracker, engine, **_):
    if len(args) < 1: print("用法: sim outcome <run_id>"); return
    run_id_prefix = args[0]
    all_cases = engine.list_cases()
    found_run = None
    for c in all_cases:
        detail = engine.get_case_detail(c["id"])
        if detail and detail.get("runs"):
            for r in detail["runs"]:
                if r["id"].startswith(run_id_prefix): found_run = r; break
        if found_run: break
    if not found_run: print(f"未找到: {run_id_prefix}"); return
    print(f"\n模型：{found_run['model_label']}")
    print(f"預測：{found_run['predicted_outcome']}")
    actual = input("實際結果：").strip()
    acc_str = input("預測準確度 (0.0~1.0)：").strip()
    accuracy = float(acc_str) if acc_str else None
    missed = input("遺漏了什麼？：").strip()
    engine.record_actual_outcome(found_run["id"], actual, accuracy, missed)
    print("✅ 實際結果已記錄。")


def cmd_report(args, db, tracker, **_):
    t = get_translation_engine(db)
    print("\n" + t.translate_report(tracker.generate_change_summary()))


def cmd_prefs_show(args, db, tracker, **_):
    pm = PreferenceManager(db)
    prefs = pm.get_preferences()
    print("\n⚙️ 當前用戶偏好：\n")
    for k, v in prefs.to_dict().items():
        print(f"  {k}: {v}")


def cmd_prefs_set(args, db, tracker, **_):
    pm = PreferenceManager(db)
    print("\n⚙️ 設置用戶偏好\n")
    intensity = float(input("干涉強度 (0.0~1.0, 默認0.3)：").strip() or "0.3")
    mode = input("干涉模式 (on_request/on_pattern/on_conclusion, 默認on_request)：").strip() or "on_request"
    lock = input("承諾鎖定 (none/light/medium/heavy, 默認light)：").strip() or "light"
    style = input("認知母語 (auto/conceptual/experiential/analogical/visual, 默認auto)：").strip() or "auto"
    pm.update_preferences(
        interference_enabled=intensity > 0,
        interference_intensity=intensity,
        interference_mode=mode,
        commitment_lock_strength=lock,
        preferred_language_style=style,
    )
    print("\n✅ 偏好已保存。")


def cmd_prefs_reset(args, db, tracker, **_):
    PreferenceManager(db).reset_to_defaults()
    print("\n✅ 偏好已重置。")


def cmd_export(args, db, tracker, **_):
    data = db.export_all()
    output_path = args[0] if args else os.path.expanduser("~/cognitive-lab-export.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"\n✅ 數據已導出到: {output_path}")


# ═══════════════════════════════════════════════
# v0.2.0 新命令
# ═══════════════════════════════════════════════

def cmd_analyze(args, db, tracker, **_):
    stdin_mode = "--stdin" in args or "-" in args
    text_args = [a for a in args if not a.startswith("-")]
    analyzer = CognitiveAnalyzer(known_schemas=db.get_all_schemas())
    if stdin_mode:
        print("📥 從 stdin 讀取（Ctrl+D 結束）...\n")
        text = sys.stdin.read().strip()
        if not text: print("沒有輸入。"); return
    elif text_args:
        text = " ".join(text_args)
    else:
        print("💭 輸入要分析的文本（空行結束）：")
        lines = []
        while True:
            line = input().strip()
            if not line: break
            lines.append(line)
        text = " ".join(lines)
        if not text: print("沒有輸入。"); return
    result = analyzer.analyze(text)
    _print_analysis_result(result)


def _print_analysis_result(result):
    print(f"\n{'='*60}")
    print(f"📊 認知分析結果")
    print(f"{'='*60}")
    print(f"\n領域：{result.domain}")
    print(f"語言風格：確定性 {result.linguistic.certainty_score:.0%} | 開放性 {result.linguistic.openness_score:.0%} | 泛化 {result.linguistic.generalization_score:.0%} | 情緒強度 {result.linguistic.emotional_intensity:.0%}")
    if result.matched_schemas:
        print(f"\n🎯 激活的思維框架：")
        for m in result.matched_schemas[:5]:
            bar = "█" * int(m.confidence * 20) + "░" * (20 - int(m.confidence * 20))
            print(f"  [{bar}] {m.label} ({m.confidence:.0%})")
            if m.matched_keywords:
                print(f"        關鍵詞：{', '.join(m.matched_keywords[:5])}")
    if result.fissures:
        print(f"\n⚠️ 檢測到 {len(result.fissures)} 個認知裂縫：")
        for f in result.fissures:
            sev_icon = "🔴" if f.severity > 0.7 else ("🟡" if f.severity > 0.4 else "🟢")
            print(f"  {sev_icon} [{f.type.value}] {f.description}")
            print(f"     嚴重度: {f.severity:.0%} | 證據: {f.evidence[:100]}...")
    if result.potential_schemas:
        print(f"\n💡 檢測到 {len(result.potential_schemas)} 個潛在新框架：")
        for p in result.potential_schemas:
            print(f"  · {p.label_candidate}")
            print(f"    {p.description_hint}")
    if result.reasoning:
        print(f"\n🧩 推理結構：")
        if result.reasoning.premises:
            print(f"  前提：{' | '.join(result.reasoning.premises[:3])}")
        if result.reasoning.conclusion:
            print(f"  結論：{result.reasoning.conclusion[:120]}")
        if result.reasoning.counter_arguments:
            print(f"  反例：{' | '.join(result.reasoning.counter_arguments[:3])}")
    print(f"\n📝 摘要：{result.summary}")
    print(f"{'='*60}\n")


def cmd_daemon(args, db, tracker, engine=None):
    from daemon.watcher import DaemonWatcher
    from daemon.pipeline import AnalysisPipeline
    from daemon.feedback import FeedbackLoop
    mode = "monitor"
    input_mode = "repl"
    file_path = None
    for i, arg in enumerate(args):
        if arg == "--mode" and i + 1 < len(args): mode = args[i + 1]
        elif arg == "--watch" and i + 1 < len(args): input_mode = "watch"; file_path = args[i + 1]
        elif arg == "--pipe": input_mode = "pipe"
    if mode not in ("silent", "monitor", "active"): mode = "monitor"
    analyzer = CognitiveAnalyzer(known_schemas=db.get_all_schemas())
    session = Session()
    prefs = PreferenceManager(db).get_preferences()
    feedback = FeedbackLoop(db, analyzer)
    pipeline = AnalysisPipeline(analyzer=analyzer, session=session, preferences=prefs, mode=mode, db=db)
    def handle_input(text: str) -> dict:
        if text == "__SUMMARY__": return {"type": "summary", "summary": session.generate_session_summary()}
        if text == "__STATS__": return pipeline.get_progress()
        result = pipeline.process(text)
        if result and result.get("type") == "log":
            ar = result.get("result")
            if ar and ar.matched_schemas:
                for m in ar.matched_schemas:
                    if m.confidence > 0.4 and m.schema_id:
                        db.increment_activation(m.schema_id)
        auto_fb = feedback.get_auto_feedback()
        if auto_fb and result: result["_auto_feedback"] = auto_fb
        return result
    watcher = DaemonWatcher(on_input=handle_input, mode=mode, input_mode=input_mode, file_path=file_path)
    try:
        watcher.start()
    finally:
        if session.results:
            print(f"\n📊 會話結束。處理了 {len(session.results)} 條輸入。")
            print(session.generate_session_summary())
            db.save_session(session.to_dict())


def cmd_feedback(args, db, tracker, engine=None):
    from daemon.feedback import FeedbackLoop
    feedback = FeedbackLoop(db)
    if args and args[0] and args[0] != "--all":
        case_id_prefix = args[0]
        all_cases = db.list_cases()
        case = next((c for c in all_cases if c["id"].startswith(case_id_prefix)), None)
        if not case: print(f"未找到案例: {case_id_prefix}"); return
        result = feedback.compare_predictions_with_outcomes(case["id"])
        if not result: print("無法獲取反饋。"); return
        _print_feedback(result)
        feedback.bulk_update_from_case(case["id"])
        print("✅ 已自動更新相關基模的有效比統計。")
    else:
        all_cases = db.list_cases()
        if not all_cases: print("還沒有任何案例。"); return
        for case in all_cases:
            result = feedback.compare_predictions_with_outcomes(case["id"])
            if result and result.get("models_with_outcomes", 0) > 0:
                print(f"\n{'─'*50}")
                _print_feedback(result, compact=True)
                feedback.bulk_update_from_case(case["id"])
        print(f"\n✅ 已更新所有案例的基模有效比統計。")


def _print_feedback(result: dict, compact: bool = False):
    print(f"\n📊 預測 vs 實際：{result.get('case', '')[:60]}")
    if result.get("status") == "no_outcomes": print(f"  {result.get('message')}"); return
    for comp in result.get("comparisons", []):
        print(f"\n  模型：{comp['model']}")
        print(f"  預測：{comp['predicted'][:100]}")
        print(f"  實際：{comp['actual'][:100]}")
        if comp.get("accuracy") is not None:
            acc = comp["accuracy"]; bar = "█" * int(acc * 20) + "░" * (20 - int(acc * 20))
            print(f"  準確度：[{bar}] {acc:.0%}")
        if comp.get("missed"): print(f"  遺漏：{comp['missed'][:100]}")
        if comp.get("schemas_used"): print(f"  使用的框架：{', '.join(comp['schemas_used'])}")
    if result.get("schema_accuracies"):
        print(f"\n  各框架平均準確度：")
        for schema, acc in result["schema_accuracies"].items():
            bar = "█" * int(acc * 20) + "░" * (20 - int(acc * 20))
            print(f"    [{bar}] {schema}: {acc:.0%}")


def cmd_growth(args, db, tracker, **_):
    from daemon.feedback import FeedbackLoop
    days = 30
    for i, arg in enumerate(args):
        if arg == "--days" and i + 1 < len(args):
            try: days = int(args[i + 1])
            except ValueError: pass
    feedback = FeedbackLoop(db)
    report = feedback.generate_growth_report(since_days=days)
    print("\n" + report)
    if feedback.should_suggest_review():
        print("\n" + feedback.generate_review_suggestion())


def cmd_status(args, db, tracker, **_):
    schemas = db.get_all_schemas()
    chains = db.get_recent_chains(limit=50)
    cases = db.list_cases()
    prefs = PreferenceManager(db).get_preferences()
    print(f"\n🧠 Cognitive Lab v0.2.0 狀態\n")
    print(f"  思維框架：{len(schemas)} 個")
    print(f"  推理鏈：{len(chains)} 條")
    print(f"  實驗室案例：{len(cases)} 個")
    active_schemas = sum(1 for s in schemas if s.get("activation_count", 0) > 0)
    print(f"  活躍框架：{active_schemas}/{len(schemas)}")
    if chains: print(f"  最近活動：{chains[0].get('timestamp', '')[:10]}")
    print(f"\n  干涉：{'開' if prefs.interference_enabled else '關'} | 強度 {prefs.interference_intensity} | 模式 {prefs.interference_mode}")
    print(f"  承諾鎖定：{prefs.commitment_lock_strength}")
    print()


COMMANDS = {
    "schema": {"list": cmd_schema_list, "add": cmd_schema_add, "graph": cmd_schema_graph},
    "chain": {"record": cmd_chain_record, "recent": cmd_chain_recent},
    "sim": {"create": cmd_sim_create, "add-run": cmd_sim_add_run, "compare": cmd_sim_compare, "list": cmd_sim_list, "outcome": cmd_sim_outcome},
    "report": cmd_report,
    "prefs": {"show": cmd_prefs_show, "set": cmd_prefs_set, "reset": cmd_prefs_reset},
    "export": cmd_export,
    "daemon": cmd_daemon,
    "analyze": cmd_analyze,
    "feedback": cmd_feedback,
    "growth": cmd_growth,
    "status": cmd_status,
}


def print_help():
    print(__doc__)


def main():
    if len(sys.argv) < 2:
        print_help()
        return
    db = Database()
    try:
        tracker = SchemaTracker(db)
        engine = SimulationEngine(db)
        command = sys.argv[1]
        args = sys.argv[2:]
        if command in COMMANDS:
            sub = COMMANDS[command]
            if isinstance(sub, dict):
                subcommand = args[0] if args else ""
                if subcommand in sub:
                    sub[subcommand](args[1:], db=db, tracker=tracker, engine=engine)
                else:
                    print(f"子命令: {list(sub.keys())}")
                    print(f"用法: cognitive-lab {command} <{'|'.join(sub.keys())}>")
            else:
                sub(args, db=db, tracker=tracker, engine=engine)
        elif command in ("-h", "--help", "help"):
            print_help()
        else:
            print(f"未知命令: {command}")
            print_help()
    finally:
        db.close()


if __name__ == "__main__":
    main()