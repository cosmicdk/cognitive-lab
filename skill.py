"""Skill interface — v0.3.0

Cognitive Lab's correct form: a function callable directly from the conversation flow.

Not a standalone CLI tool. Not a background daemon. Not an observer outside the conversation loop.
It's a function called when AI generates a response, that directly improves the output.

Usage:
    from cognitive_lab.skill import enhance_response

    result = enhance_response(
        user_query="Should I leave my job to start a company?",
        ai_draft="If you leave, you may face income loss and failure risk...",
        user_history=["I've always been torn about career choices", "Last job switch was hard"],
        user_schemas=["SafetyFirst", "ZeroSum"]
    )

    # result has:
    #   - has_issues: bool
    #   - improved_response: str | None
    #   - warnings: list
    #   - analysis: dict

Also:
    from cognitive_lab.skill import quick_check, analyze_conversation_pair
"""

import re
from typing import Optional, List, Dict
from dataclasses import dataclass, field


@dataclass
class EnhancementResult:
    has_issues: bool = False
    improved_response: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
    analysis: dict = field(default_factory=dict)


CERTAINTY_WORDS_ZH = [
    "一定", "绝对", "肯定", "必然", "毫无疑问", "毋庸置疑",
    "显然", "从来都是", "永远都是", "不可能", "绝不会", "必定",
]
CERTAINTY_WORDS_EN = [
    "definitely", "absolutely", "certainly", "undoubtedly",
    "always", "never", "must be", "no doubt", "inevitably",
]
OVERGENERALIZE_ZH = ["总是", "每次", "从不", "一直", "永远", "所有人", "没人", "全都是"]
OVERGENERALIZE_EN = ["always", "never", "everyone", "nobody", "everything", "nothing"]

COUNTERBALANCE_WORDS = [
    "不过", "但是", "然而", "另一方面", "但也", "例外",
    "however", "on the other hand", "alternatively",
    "不一定", "取决于", "看情况", "it depends",
    "换个角度", "另一种可能是",
]

AVOIDANCE_WORDS_ZH = [
    "需要更多信息", "很难说", "取决于很多因素", "因人而异",
    "这个问题的答案很复杂", "没有标准答案",
]

FRAMEWORK_PATTERNS = [
    {
        "name": "ZeroSum",
        "patterns": ["win.*lose", "zero.sum", "零和", "此消彼长", "有限资源"],
        "opposite": "Abundance",
        "opposite_prompt": "Could resources grow through innovation and collaboration, rather than being fixed?"
    },
    {
        "name": "SafetyFirst",
        "patterns": ["风险", "稳定", "安全", "保守", "失败率", "退路", "保险", "确定", "risk", "safe"],
        "opposite": "GrowthOriented",
        "opposite_prompt": "Consider: what is the cost of not taking a risk? What are the hidden costs of stability?"
    },
    {
        "name": "Anchoring",
        "patterns": ["百分之[0-9]+", "[0-9]+%", "平均", "大多数.*不", "绝大部分"],
        "opposite": "BaseRateReview",
        "opposite_prompt": "Does this statistic apply to this specific situation? Group statistics don't always apply to individuals."
    },
    {
        "name": "ConfirmationBias",
        "patterns": ["正是", "果然", "我就说", "证明了我", "说明我是对的"],
        "opposite": "Falsification",
        "opposite_prompt": "Try assuming your view is wrong first, and then look for evidence against it."
    },
    {
        "name": "BinaryThinking",
        "patterns": ["要么.*要么", "二选一", "只能", "非黑即白"],
        "opposite": "SpectrumThinking",
        "opposite_prompt": "Is this really a binary choice? Could there be a third path, or shades of gray between the two options?"
    },
    {
        "name": "Catastrophizing",
        "patterns": ["完蛋", "没救了", "万劫不复", "毁掉", "不可挽回"],
        "opposite": "ProbabilityCalibration",
        "opposite_prompt": "What is the actual probability of the worst case? Even if it happens, is there a way to deal with it?"
    },
]


def enhance_response(
    user_query: str,
    ai_draft: str,
    user_history: List[str] = None,
    user_schemas: List[str] = None,
    mode: str = "auto",
) -> EnhancementResult:
    """Analyze AI response draft, detect cognitive issues, generate improved version.

    Args:
        user_query: user's latest question
        ai_draft: AI's draft response
        user_history: recent conversation history (optional)
        user_schemas: user's known cognitive schema names (optional)
        mode: "analyze_only" | "auto" | "suggest"

    Returns:
        EnhancementResult with has_issues, warnings, analysis, and optionally improved_response
    """
    result = EnhancementResult()
    analysis = {}
    warnings = []

    draft_lower = ai_draft.lower() if ai_draft else ""

    # 1. Single framework bias
    if user_schemas:
        matched_schemas = []
        for schema_name in user_schemas:
            keywords = _extract_keywords(schema_name)
            if any(kw.lower() in draft_lower for kw in keywords):
                matched_schemas.append(schema_name)

        active_count = len(matched_schemas)
        total_count = len(user_schemas)
        analysis["schema_coverage"] = {
            "matched": matched_schemas,
            "total_available": total_count,
            "coverage_ratio": active_count / total_count if total_count > 0 else 0,
        }

        if total_count >= 2 and active_count <= total_count * 0.3 and active_count == 1:
            unused = [s for s in user_schemas if s not in matched_schemas]
            warnings.append(
                f"Response uses only 1 framework ({matched_schemas[0]}), "
                f"but user has {total_count} known frameworks. "
                f"Also consider: {' / '.join(unused[:2])}"
            )
            analysis["single_framework_warning"] = True
            analysis["missing_perspectives"] = unused

    # 2. Over-certainty
    cert_count = sum(
        1 for w in CERTAINTY_WORDS_ZH + CERTAINTY_WORDS_EN
        if w.lower() in draft_lower
    )
    analysis["certainty_words"] = cert_count
    if cert_count >= 3:
        warnings.append(
            f"Response uses {cert_count} certainty words (e.g. 'definitely/absolutely/always'). "
            f"Suggest adding qualifiers like 'based on current information' or 'in most cases'."
        )

    # 3. Missing counterbalance
    has_counterbalance = any(w.lower() in draft_lower for w in COUNTERBALANCE_WORDS)
    analysis["has_counterbalance"] = has_counterbalance
    if not has_counterbalance and len(ai_draft) > 200:
        warnings.append(
            "Response lacks any counter-argument or balancing statement "
            "(e.g. 'however/on the other hand/it depends'). Only one side presented."
        )

    # 4. Overgeneralization
    overgen_count = sum(
        1 for w in OVERGENERALIZE_ZH + OVERGENERALIZE_EN
        if w.lower() in draft_lower
    )
    analysis["overgeneralization_words"] = overgen_count
    if overgen_count >= 2:
        warnings.append(
            f"Response uses {overgen_count} overgeneralizing words "
            f"(e.g. 'always/never/everyone'). Suggest more precise descriptions."
        )

    # 5. Avoidance
    has_avoidance = any(w in ai_draft for w in AVOIDANCE_WORDS_ZH)
    analysis["possible_avoidance"] = has_avoidance
    if has_avoidance:
        avoidance_count = sum(1 for w in AVOIDANCE_WORDS_ZH if w in ai_draft)
        if avoidance_count >= 2 and len(ai_draft) < 300:
            warnings.append(
                "Response appears to avoid giving specific advice "
                "(uses 'it depends/varies by person' multiple times without offering a concrete framework)."
            )

    # 6. Cognitive framework detection
    detected_frameworks = []
    for fp in FRAMEWORK_PATTERNS:
        matched_patterns = [p for p in fp["patterns"] if re.search(p, ai_draft)]
        if matched_patterns:
            detected_frameworks.append({
                "name": fp["name"],
                "opposite": fp["opposite"],
                "opposite_prompt": fp["opposite_prompt"],
            })

    analysis["detected_cognitive_frameworks"] = [
        {"name": df["name"], "opposite": df["opposite"]}
        for df in detected_frameworks
    ]

    if detected_frameworks:
        names = [df["name"] for df in detected_frameworks]
        opposites = [df["opposite"] for df in detected_frameworks]
        prompt = "; ".join(df["opposite_prompt"] for df in detected_frameworks)
        warnings.append(
            f"Detected cognitive patterns in response: {', '.join(names)}. "
            f"Consider adding {'/'.join(opposites)} perspective."
        )
        analysis["framework_opposites_needed"] = opposites
        analysis["opposite_prompt"] = prompt

    # 7. History repetition
    if user_history and len(user_history) >= 2:
        history_check = _check_repetition(ai_draft, user_history[-3:])
        analysis["history_repetition"] = history_check
        if history_check.get("is_repeating"):
            warnings.append(
                "Response structure is highly similar to recent responses. "
                "Long-term use of the same framework can make different questions look alike."
            )

    result.analysis = analysis
    result.warnings = warnings
    result.has_issues = len(warnings) > 0

    if not result.has_issues:
        return result

    if mode == "analyze_only":
        return result

    if mode == "auto":
        result.improved_response = _build_improved_response(ai_draft, analysis, warnings)
    elif mode == "suggest":
        result.improved_response = ai_draft + "\n\n---\n\n" + _build_suggestions(warnings, analysis)

    return result


def _extract_keywords(label: str) -> List[str]:
    words = re.findall(r'[\u4e00-\u9fff]{2,4}|[a-zA-Z]{3,}', label)
    return [w for w in words if w.lower() not in ("1", "2", "3")]


def _check_repetition(draft: str, history: List[str]) -> dict:
    draft_lower = draft.lower()
    draft_phrases = set(re.findall(r'[\u4e00-\u9fff]{4,}', draft_lower))
    similar_count = 0
    for h in history:
        h_phrases = set(re.findall(r'[\u4e00-\u9fff]{4,}', h.lower()))
        if len(draft_phrases & h_phrases) >= 5:
            similar_count += 1
    return {"is_repeating": similar_count >= 2, "similar_to_count": similar_count}


def _build_improved_response(original: str, analysis: dict, warnings: List[str]) -> str:
    lines = original.strip().split("\n")
    improved = []

    if analysis.get("single_framework_warning") and analysis.get("missing_perspectives"):
        missing = analysis["missing_perspectives"]
        prompt = analysis.get("opposite_prompt", "")
        improved.append(f"*(This analysis tries to consider {'/'.join(missing[:2])} perspectives as well. {prompt})*\n")

    added_counterbalance = False
    for i, line in enumerate(lines):
        improved.append(line)
        if not added_counterbalance and i > 1 and len(line) > 80:
            if any(w in line for w in CERTAINTY_WORDS_ZH):
                opposite = analysis.get("opposite_prompt", "")
                if opposite:
                    improved.append(f"\n*[Additional perspective] {opposite}*\n")
                else:
                    improved.append("\n*However, also consider: are the judgments above based on unexamined assumptions? Different frameworks may yield different conclusions.*\n")
                added_counterbalance = True

    if not added_counterbalance and not analysis.get("has_counterbalance"):
        improved.append("\n---\n*Note: This analysis comes from one specific perspective. Different frameworks applied to the same problem may yield different conclusions. Try switching lenses.*")

    return "\n".join(improved)


def _build_suggestions(warnings: List[str], analysis: dict) -> str:
    parts = ["**[Cognitive Notes]**"]
    for w in warnings[:3]:
        parts.append(f"- {w}")
    if analysis.get("missing_perspectives"):
        parts.append(f"- Suggested additional perspective: {' / '.join(analysis['missing_perspectives'][:2])}")
    return "\n".join(parts)


def quick_check(ai_draft: str) -> dict:
    """Minimal call: just check AI response quality"""
    result = enhance_response(user_query="", ai_draft=ai_draft, mode="analyze_only")
    return {"has_issues": result.has_issues, "warnings": result.warnings}


def analyze_conversation_pair(
    user_says: str,
    ai_says: str,
    known_schemas: List[str] = None,
) -> dict:
    """Analyze one round of conversation quality"""
    result = enhance_response(
        user_query=user_says,
        ai_draft=ai_says,
        user_schemas=known_schemas,
    )
    cert_count = result.analysis.get("certainty_words", 0)
    return {
        "framework_bias": result.analysis.get("schema_coverage", {}),
        "certainty_level": "high" if cert_count >= 3 else ("medium" if cert_count >= 1 else "low"),
        "balance_score": 0.7 if result.analysis.get("has_counterbalance") else 0.3,
        "avoidance_detected": result.analysis.get("possible_avoidance", False),
        "detected_frameworks": result.analysis.get("detected_cognitive_frameworks", []),
        "suggestions": [w for w in result.warnings],
    }