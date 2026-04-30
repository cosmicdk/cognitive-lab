"""Skill: AI Response Cognitive Quality Detector — A Skill That Does One Thing Well

One file. Zero dependencies. Three functions. Drop into any AI conversation system.

Detects 5 issues in AI responses: single-framework bias, over-certainty, 
missing counterbalance, overgeneralization, and avoidance.

Usage:
    from cognitive_lab.skill import enhance_response, quick_check

    result = enhance_response(user_query, ai_draft, user_schemas=["SafetyFirst", "Abundance"])
    if result.has_issues:
        return result.improved_response
"""

import re
from typing import List, Optional
from dataclasses import dataclass, field


@dataclass
class EnhancementResult:
    has_issues: bool = False
    improved_response: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
    analysis: dict = field(default_factory=dict)


# ── Detection lexicons ──

CERTAINTY = [
    "一定", "绝对", "肯定", "必然", "毫无疑问", "毋庸置疑",
    "显然", "不可能", "绝不会", "必定", "注定", "唯一.*正确",
    "definitely", "absolutely", "certainly", "undoubtedly", "must be", "no doubt",
]

OVERGENERALIZE = [
    "总是", "每次", "从不", "一直", "永远", "所有人", "没人", "全都是",
    "always", "never", "everyone", "nobody", "everything", "nothing",
]

COUNTERBALANCE = [
    "不过", "但是", "然而", "另一方面", "但也", "例外",
    "however", "on the other hand", "alternatively",
    "不一定", "取决于", "看情况", "it depends", "换个角度",
]

AVOIDANCE = [
    "需要更多信息", "很难说", "因人而异", "没有标准答案",
    "这个问题的答案很复杂",
]

# Framework patterns: each needs >=2 pattern hits to trigger (reduces false positives)
FRAMEWORKS = [
    ("ZeroSum", ["win.*lose", "零和", "此消彼长", "有限资源", "一方赢.*一方输"], "Abundance",
     "Could resources grow through innovation and collaboration rather than being fixed?"),
    ("SafetyFirst", ["risk.*too high", "failure rate.{0,5}[0-9]+%", "safest.*is", "退路", "稳定.*最重要"], "GrowthOriented",
     "What's the cost of NOT taking a risk? What are the hidden costs of stability?"),
    ("Anchoring", ["[0-9]+%.{0,10}fail", "average.*not", "most.*don't", "百分之[0-9]+", "绝大部分.*不"], "BaseRateReview",
     "Do these statistics apply to this specific situation? Group stats don't always apply to individuals."),
    ("ConfirmationBias", ["just as I said", "this proves", "I told you", "正是.*证明", "说明我是对的"], "Falsification",
     "Try assuming your view is wrong first, then look for evidence against it."),
    ("BinaryThinking", ["either.*or", "二选一", "只能.*不能", "非黑即白"], "SpectrumThinking",
     "Is this really a binary choice? Could there be a third path?"),
    ("Catastrophizing", ["完蛋", "没救了", "万劫不复", "不可挽回", "毁掉"], "ProbabilityCalibration",
     "What's the actual probability of the worst case? Even if it happens, what's the response?"),
]


# ── Core functions ──

def enhance_response(
    user_query: str = "",
    ai_draft: str = "",
    user_schemas: List[str] = None,
    mode: str = "auto",
) -> EnhancementResult:
    """Analyze AI response draft, detect cognitive issues, optionally return improved version.

    Args:
        user_query: user's question
        ai_draft: AI's draft response
        user_schemas: user's known cognitive schema names (e.g. ["SafetyFirst", "Abundance"])
        mode: "analyze_only" | "auto" | "suggest"

    Returns:
        EnhancementResult(has_issues, improved_response, warnings, analysis)
    """
    draft = ai_draft or ""
    draft_lower = draft.lower()
    result = EnhancementResult()
    warnings = []
    analysis = {}

    # 1. Over-certainty (threshold: >=2 words)
    cert_hits = [w for w in CERTAINTY if w.lower() in draft_lower or re.search(w, draft)]
    analysis["certainty_count"] = len(cert_hits)
    analysis["certainty_words"] = cert_hits[:5]
    if len(cert_hits) >= 2:
        warnings.append(
            f"Uses {len(cert_hits)} certainty words ({', '.join(cert_hits[:3])}...). "
            f"Suggest adding qualifiers like 'based on current information' or 'in most cases'."
        )

    # 2. Missing counterbalance
    has_counterbalance = any(w.lower() in draft_lower for w in COUNTERBALANCE)
    analysis["has_counterbalance"] = has_counterbalance
    if not has_counterbalance and len(draft) > 150:
        warnings.append(
            "Response lacks counterbalancing statements (e.g. 'however/on the other hand/it depends'). "
            "May present only one side."
        )

    # 3. Overgeneralization
    overgen_hits = [w for w in OVERGENERALIZE if w.lower() in draft_lower]
    analysis["overgeneralization_count"] = len(overgen_hits)
    if len(overgen_hits) >= 2:
        warnings.append(
            f"Uses {len(overgen_hits)} overgeneralizing words ({', '.join(overgen_hits[:3])}...). "
            f"Suggest more precise descriptions."
        )

    # 4. Avoidance
    avoidance_hits = [w for w in AVOIDANCE if w in draft]
    analysis["avoidance_count"] = len(avoidance_hits)
    if len(avoidance_hits) >= 2:
        warnings.append(
            "Response uses multiple avoidance phrases ('it depends/varies by person') "
            "without offering a concrete framework. Appears to dodge giving specific advice."
        )

    # 5. Single-framework bias
    if user_schemas and len(user_schemas) >= 2:
        matched = [s for s in user_schemas if _schema_matches(s, draft_lower)]
        analysis["schema_coverage"] = {
            "matched": matched, "total": len(user_schemas),
            "ratio": len(matched) / len(user_schemas),
        }
        if len(matched) == 1 and len(user_schemas) >= 3:
            unused = [s for s in user_schemas if s not in matched]
            warnings.append(
                f"Response only uses '{matched[0]}' perspective, "
                f"but user has {len(user_schemas)} known frameworks. "
                f"Also consider: {'/'.join(unused[:2])}"
            )
            analysis["missing_perspectives"] = unused

    # 6. Framework pattern detection (only alarm when no counterbalance)
    detected = []
    for name, patterns, opposite, prompt in FRAMEWORKS:
        hits = [p for p in patterns if re.search(p, draft)]
        if len(hits) >= 2:  # need >=2 pattern hits to reduce false positives
            detected.append({"name": name, "opposite": opposite, "prompt": prompt})

    analysis["detected_frameworks"] = [{"name": d["name"]} for d in detected]

    if detected and not has_counterbalance:
        names = [d["name"] for d in detected]
        opposites = [d["opposite"] for d in detected]
        prompts = [d["prompt"] for d in detected]
        warnings.append(
            f"Detected '{', '.join(names)}' thinking pattern. "
            f"Suggest adding {'/'.join(opposites)} perspective: {'; '.join(prompts)}"
        )
        analysis["opposite_prompts"] = prompts

    result.warnings = warnings
    result.analysis = analysis
    result.has_issues = len(warnings) > 0

    if not result.has_issues:
        return result

    if mode == "auto":
        result.improved_response = _improve(draft, analysis)
    elif mode == "suggest":
        result.improved_response = draft + "\n\n---\n**Cognitive Notes**\n" + \
            "\n".join(f"- {w}" for w in warnings)

    return result


def quick_check(ai_draft: str, user_schemas: List[str] = None) -> dict:
    """One-liner: check AI response quality.
    
    >>> quick_check("This is definitely wrong, you absolutely must act now.")
    {'has_issues': True, 'warnings': [...], 'score': 0.6}
    """
    result = enhance_response(ai_draft=ai_draft, user_schemas=user_schemas, mode="analyze_only")
    score = _compute_score(result)
    return {"has_issues": result.has_issues, "warnings": result.warnings, "score": score}


def analyze_pair(user_says: str, ai_says: str, schemas: List[str] = None) -> dict:
    """Analyze one round of conversation quality.
    
    Returns: {certainty_level, balance_score, frameworks_detected, suggestions}
    """
    result = enhance_response(user_query=user_says, ai_draft=ai_says, user_schemas=schemas)
    cert = result.analysis.get("certainty_count", 0)
    return {
        "certainty_level": "high" if cert >= 3 else ("medium" if cert >= 1 else "low"),
        "balance_score": 0.7 if result.analysis.get("has_counterbalance") else 0.3,
        "frameworks_detected": result.analysis.get("detected_frameworks", []),
        "suggestions": result.warnings,
    }


# ── Internal helpers ──

def _schema_matches(name: str, text: str) -> bool:
    keywords = re.findall(r'[\u4e00-\u9fff]{2,4}|[a-zA-Z]{3,}', name)
    return any(kw.lower() in text for kw in keywords if kw.lower() not in ("1", "2", "3"))


def _compute_score(result: EnhancementResult) -> float:
    a = result.analysis
    score = 1.0
    if a.get("certainty_count", 0) >= 2: score -= 0.2
    if not a.get("has_counterbalance"): score -= 0.2
    if a.get("overgeneralization_count", 0) >= 2: score -= 0.15
    if a.get("avoidance_count", 0) >= 2: score -= 0.15
    if a.get("detected_frameworks"): score -= 0.1 * len(a["detected_frameworks"])
    return max(0.0, round(score, 2))


def _improve(draft: str, analysis: dict) -> str:
    lines = draft.strip().split("\n")
    out = []
    missing = analysis.get("missing_perspectives", [])
    prompts = analysis.get("opposite_prompts", [])
    if missing:
        out.append(f"*(This analysis also considers {'/'.join(missing[:2])} perspectives. {'; '.join(prompts[:2])})*\n")
    inserted = False
    for i, line in enumerate(lines):
        out.append(line)
        if not inserted and i > 1 and len(line) > 60:
            if any(w in line for w in ["一定", "绝对", "肯定", "必然", "不可能"]):
                if not analysis.get("has_counterbalance"):
                    prompt_text = prompts[0] if prompts else \
                        "Are the judgments above based on unexamined assumptions? Different frameworks may yield different conclusions."
                    out.append(f"\n*[Additional perspective] {prompt_text}*\n")
                    inserted = True
    if not inserted and not analysis.get("has_counterbalance"):
        out.append("\n---\n*Note: This analysis comes from one specific perspective. Different frameworks may yield different conclusions.*")
    return "\n".join(out)


analyze_conversation_pair = analyze_pair  # backward-compat alias