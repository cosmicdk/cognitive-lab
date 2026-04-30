"""认知母语适配层 — 小蛇 R5"""

from typing import Dict, List


class TranslationEngine:
    STYLES = ["conceptual", "experiential", "analogical", "visual", "auto"]
    
    CONCEPT_TRANSLATIONS = {
        "schema": {"conceptual": "思维框架", "experiential": "你常用的思考方式", "analogical": "脑子里的地图", "visual": "🧠 思考模式"},
        "blind_spot": {"conceptual": "认知盲区", "experiential": "你还没注意到的地方", "analogical": "后脑勺——自己看不见的那一面", "visual": "🔍 未覆盖区域"},
        "pattern": {"conceptual": "推理模式", "experiential": "你反复使用的思路", "analogical": "走熟的老路", "visual": "📊 重复路径"},
        "interference": {"conceptual": "认知干涉", "experiential": "一个提醒", "analogical": "路口的一个路标", "visual": "💡 提示"},
        "simulation": {"conceptual": "思维模拟", "experiential": "在脑子里试一遍", "analogical": "沙盘推演——像下棋前先摆一摆", "visual": "🧪 沙盘模拟"},
        "prediction_accuracy": {"conceptual": "预测准确度", "experiential": "你猜对了多少", "analogical": "天气预报准不准", "visual": "🎯 命中率"},
    }
    
    def __init__(self, style: str = "auto"):
        self.style = style if style in self.STYLES else "auto"
    
    def translate(self, term: str, context: str = "") -> str:
        t = self.CONCEPT_TRANSLATIONS.get(term, {})
        if not t: return term
        if self.style == "auto": return t.get("experiential", t.get("conceptual", term))
        return t.get(self.style, term)
    
    def translate_report(self, report: str) -> str:
        if self.style == "conceptual": return report
        for term, translations in self.CONCEPT_TRANSLATIONS.items():
            cl = translations.get("conceptual", term)
            tl = translations.get(self.style, cl)
            if cl != tl: report = report.replace(cl, tl)
        return report
    
    def generate_explanation(self, concept: str, user_schemas: List[Dict] = None) -> str:
        explanations = {
            "schema_tracker": {
                "conceptual": "认知基模追踪器记录并分析你在不同情境中反复使用的思维框架。",
                "experiential": "帮你留意自己常用的思考方式——比如遇到问题总是先想最坏还是最好情况？",
                "analogical": "像在脑子里装了个GPS——不告诉你去哪，但会记录你常走的路。回头看你发现有些路走了很多遍，有些从没试过。",
                "visual": "🧠→📊 把你的思考过程画成地图。",
            },
            "simulation_engine": {
                "conceptual": "思维实验室允许你用不同思维模型分析同一问题，对比预测，看到单一视角的局限。",
                "experiential": "做决策前先在脑子里试一遍。用悲观角度试一次，乐观角度再试一次，看结果有什么不同。",
                "analogical": "像风洞测试——工程师不直接把新机翼装飞机上，而是先在风洞里吹。思维实验室就是你的认知风洞。",
                "visual": "🧪 你的思维风洞：放入问题，用3个不同角度同时测试。",
            },
            "pattern_detector": {
                "conceptual": "模式检测器识别推理链中与历史重复的结构，在旧框架即将闭合时提醒你。",
                "experiential": "它会注意你是不是又在用同样的思路想问题——尤其上次没带来好结果时，轻轻提醒你。",
                "analogical": "像走在森林里，有人在你耳边说：你上次走这条路绕了一大圈。这次要不要试试旁边那条？不强迫，只提醒。",
                "visual": "🔄 模式雷达：标记这好像走过的路口。",
            },
        }
        exp = explanations.get(concept, {})
        if self.style == "auto": return exp.get("experiential", exp.get("conceptual", "暂无解释。"))
        return exp.get(self.style, exp.get("conceptual", "暂无解释。"))
    
    def set_style(self, style: str):
        if style in self.STYLES: self.style = style