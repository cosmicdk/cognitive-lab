#!/usr/bin/env python3
"""认知实验室 CLI — MVP 入口

用法：
  cognitive-lab schema list          # 列出所有认知基模
  cognitive-lab schema add            # 交互式添加基模
  cognitive-lab schema graph          # 导出认知基模图
  cognitive-lab chain record          # 记录一条推理链
  cognitive-lab chain recent          # 查看最近的推理链
  cognitive-lab sim create            # 创建思维实验室案例
  cognitive-lab sim compare <case_id> # 多模型对比
  cognitive-lab sim outcome <run_id>  # 记录实际结果
  cognitive-lab report                # 生成认知变化摘要
  cognitive-lab prefs show            # 查看当前偏好
  cognitive-lab prefs set             # 设置偏好
  cognitive-lab export                # 导出全部数据
"""

import sys, os, json
from datetime import datetime

_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _project_root)

from storage.database import Database
from core.schema_tracker import SchemaTracker
from core.simulation_engine import SimulationEngine
from core.models import SchemaDomain, SchemaConfidence, ReasoningChain, ReasoningStep
from control.preferences import PreferenceManager
from core.translation import TranslationEngine


def get_translation_engine(db):
    prefs = PreferenceManager(db).get_preferences()
    return TranslationEngine(style=prefs.preferred_language_style)


def cmd_schema_list(args, db, tracker, **_):
    t = get_translation_engine(db)
    schemas = db.get_all_schemas()
    if not schemas:
        print("还没有记录任何思维框架。使用 `schema add` 添加第一个。")
        return
    print(f"\n📊 {t.translate('schema')} 地图（共 {len(schemas)} 个节点）\n")
    icons = {"unquestioned": "⚪", "examined": "🔍", "tentative": "🌱", "revised": "🔄", "abandoned": "💤"}
    for s in schemas:
        icon = icons.get(s.get("confidence", ""), "❓")
        print(f"  {icon} [{s.get('domain', '')}] {s['label']}")
        print(f"     激活 {s.get('activation_count', 0)} 次 | 有效比: ", end="")
        total = s.get("successful_applications", 0) + s.get("unsuccessful_applications", 0)
        print(f"{s['successful_applications']/total:.0%}" if total > 0 else "暂无数据")
        if s.get("description"): print(f"     {s['description'][:80]}")
        print()


def cmd_schema_add(args, db, tracker, **_):
    print("\n🆕 添加新的思维框架\n")
    label = input("名称（简短标签）：").strip()
    if not label: print("已取消。"); return
    description = input("详细描述：").strip()
    print("\n领域：professional / relational / self_identity / learning / worldview / technical")
    domain_input = input("选择（直接回车=uncategorized）：").strip()
    try: domain = SchemaDomain(domain_input) if domain_input else SchemaDomain.UNCATEGORIZED
    except ValueError: domain = SchemaDomain.UNCATEGORIZED
    print("\n确信程度：unquestioned / examined / tentative / revised / abandoned")
    conf_input = input("选择（直接回车=tentative）：").strip()
    try: confidence = SchemaConfidence(conf_input) if conf_input else SchemaConfidence.TENTATIVE
    except ValueError: confidence = SchemaConfidence.TENTATIVE
    sid = tracker.register_schema(label=label, description=description, domain=domain, confidence=confidence)
    print(f"\n✅ 框架已注册，ID: {sid[:8]}...")


def cmd_schema_graph(args, db, tracker, **_):
    print(json.dumps(tracker.export_graph_json(), ensure_ascii=False, indent=2))


def cmd_chain_record(args, db, tracker, **_):
    print("\n📝 记录推理链\n")
    topic = input("推理主题：").strip()
    if not topic: print("已取消。"); return
    steps = []
    print("输入推理步骤（空行结束）：")
    i = 1
    while True:
        content = input(f"  步骤 {i}：").strip()
        if not content: break
        is_conclusion = input(f"  这是最终结论吗？(y/n)：").strip().lower() == "y"
        steps.append(ReasoningStep(step_index=i, content=content, activated_schema_ids=[], is_conclusion=is_conclusion))
        i += 1
    if not steps: print("没有输入任何步骤。"); return
    schemas = db.get_all_schemas()
    print("\n🔗 自动匹配已有思维框架...")
    for step in steps:
        for s in schemas:
            if any(kw in step.content.lower() for kw in s["label"].lower().split()):
                step.activated_schema_ids.append(s["id"])
                print(f"  步骤 {step.step_index} 匹配到：{s['label']}")
    chain = ReasoningChain(session_id=f"cli-{datetime.now().strftime('%Y%m%d-%H%M%S')}", topic=topic, steps=steps)
    db.save_chain(chain.to_dict())
    for step in steps:
        for sid in step.activated_schema_ids: db.increment_activation(sid)
    print(f"\n✅ 推理链已保存，ID: {chain.id[:8]}...")


def cmd_chain_recent(args, db, tracker, **_):
    chains = db.get_recent_chains(limit=10)
    if not chains: print("还没有任何推理链记录。"); return
    print(f"\n📋 最近 {len(chains)} 条推理链：\n")
    for c in chains:
        sat = "😊" if c.get("outcome_satisfaction") is True else ("😞" if c.get("outcome_satisfaction") is False else "❓")
        print(f"  {sat} [{c['id'][:8]}] {c['topic']}")
        print(f"     {c['timestamp'][:19]} | {len(c.get('steps', []))} 步")
        if c.get("reflection"): print(f"     反思：{c['reflection'][:60]}")
        print()


def cmd_sim_create(args, db, tracker, engine, **_):
    print("\n🧪 创建思维实验室案例\n")
    problem = input("描述你要分析的问题：").strip()
    if not problem: print("已取消。"); return
    print("\n领域：professional / relational / self_identity / learning / worldview / technical")
    domain_input = input("选择（回车=uncategorized）：").strip()
    try: domain = SchemaDomain(domain_input) if domain_input else SchemaDomain.UNCATEGORIZED
    except ValueError: domain = SchemaDomain.UNCATEGORIZED
    case_id = engine.create_case(problem, domain)
    print(f"\n✅ 案例已创建，ID: {case_id[:8]}...")
    print(f"添加模型：cognitive-lab sim add-run {case_id[:8]}")


def cmd_sim_add_run(args, db, tracker, engine, **_):
    if len(args) < 1: print("用法: sim add-run <case_id>"); return
    case = next((c for c in engine.list_cases() if c["id"].startswith(args[0])), None)
    if not case: print(f"未找到案例: {args[0]}"); return
    print(f"\n案例：{case['problem_statement'][:80]}")
    model_label = input("思维模型名称：").strip()
    predicted = input("预测结果：").strip()
    conf = float(input("信心度 (0~1，回车=0.5)：").strip() or "0.5")
    rid = engine.add_run(case_id=case["id"], model_label=model_label, predicted_outcome=predicted, confidence=conf)
    print(f"✅ 运行已添加。用 `sim outcome {rid[:8]}` 记录实际结果。")


def cmd_sim_compare(args, db, tracker, engine, **_):
    if len(args) < 1: print("用法: sim compare <case_id>"); return
    case = next((c for c in engine.list_cases() if c["id"].startswith(args[0])), None)
    if not case: print(f"未找到案例: {args[0]}"); return
    print("\n" + (engine.get_comparison(case["id"]) or "无数据。"))


def cmd_sim_list(args, db, tracker, engine, **_):
    cases = engine.list_cases()
    if not cases: print("还没有任何案例。"); return
    print(f"\n🧪 思维实验室案例（共 {len(cases)} 个）：\n")
    for c in cases:
        print(f"  📋 [{c['id'][:8]}] {c['problem_statement'][:60]}")
        print(f"     {c['domain']} | {c['created_at'][:19]}")


def cmd_sim_outcome(args, db, tracker, engine, **_):
    if len(args) < 1: print("用法: sim outcome <run_id>"); return
    found = None
    for c in engine.list_cases():
        detail = engine.get_case_detail(c["id"])
        if detail:
            for r in detail.get("runs", []):
                if r["id"].startswith(args[0]): found = r; break
        if found: break
    if not found: print(f"未找到运行: {args[0]}"); return
    print(f"\n模型：{found['model_label']}")
    print(f"预测：{found['predicted_outcome']}")
    actual = input("实际结果：").strip()
    acc = input("预测准确度 (0~1，回车跳过)：").strip()
    missed = input("遗漏了什么？（回车跳过）：").strip()
    engine.record_actual_outcome(found["id"], actual, float(acc) if acc else None, missed)
    print("✅ 实际结果已记录。")


def cmd_report(args, db, tracker, **_):
    t = get_translation_engine(db)
    print("\n" + t.translate_report(tracker.generate_change_summary()))


def cmd_prefs_show(args, db, tracker, **_):
    prefs = PreferenceManager(db).get_preferences()
    print("\n⚙️ 当前用户偏好：\n")
    for k, v in prefs.to_dict().items(): print(f"  {k}: {v}")


def cmd_prefs_set(args, db, tracker, **_):
    pm = PreferenceManager(db)
    print("\n⚙️ 设置用户偏好\n")
    intensity = float(input("干涉强度 (0.0=仅观察, 1.0=积极挑战，默认0.3)：").strip() or "0.3")
    print("干涉模式：on_request / on_pattern / on_conclusion")
    mode = input("选择 (默认 on_request)：").strip() or "on_request"
    print("承诺锁定强度：none / light / medium / heavy")
    lock = input("选择 (默认 light)：").strip() or "light"
    print("认知母语风格：auto / conceptual / experiential / analogical / visual")
    style = input("选择 (默认 auto)：").strip() or "auto"
    pm.update_preferences(interference_enabled=intensity > 0, interference_intensity=intensity,
                          interference_mode=mode, commitment_lock_strength=lock, preferred_language_style=style)
    print("\n✅ 偏好已保存。")


def cmd_export(args, db, tracker, **_):
    data = db.export_all()
    out = args[0] if args else os.path.expanduser("~/cognitive-lab-export.json")
    with open(out, "w", encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"\n✅ 数据已导出到: {out}")
    print(f"  包含 {len(data['schemas'])} 个框架、{len(data['chains'])} 条推理链、{len(data['cases'])} 个案例")


COMMANDS = {
    "schema": {"list": cmd_schema_list, "add": cmd_schema_add, "graph": cmd_schema_graph},
    "chain": {"record": cmd_chain_record, "recent": cmd_chain_recent},
    "sim": {"create": cmd_sim_create, "add-run": cmd_sim_add_run, "compare": cmd_sim_compare,
            "list": cmd_sim_list, "outcome": cmd_sim_outcome},
    "report": cmd_report,
    "prefs": {"show": cmd_prefs_show, "set": cmd_prefs_set, "reset": lambda a, **kw: PreferenceManager(kw['db']).reset_to_defaults() or print("\n✅ 偏好已重置。")},
    "export": cmd_export,
}


def main():
    if len(sys.argv) < 2: print(__doc__); return
    db = Database()
    try:
        tracker = SchemaTracker(db)
        engine = SimulationEngine(db)
        cmd, args = sys.argv[1], sys.argv[2:]
        if cmd in COMMANDS:
            sub = COMMANDS[cmd]
            if isinstance(sub, dict):
                sc = args[0] if args else ""
                if sc in sub: sub[sc](args[1:], db=db, tracker=tracker, engine=engine)
                else: print(f"子命令: {list(sub.keys())}")
            else: sub(args, db=db, tracker=tracker, engine=engine)
        elif cmd in ("-h", "--help", "help"): print(__doc__)
        else: print(f"未知命令: {cmd}"); print(__doc__)
    finally: db.close()


if __name__ == "__main__": main()