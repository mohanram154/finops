import re
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

# ============================================================================
# Enumerations for Structured Request Analysis
# ============================================================================
class TaskType(str, Enum):
    CLASSIFICATION = "classification"
    TRANSLATION = "translation"
    SUMMARIZATION = "summarization"
    EXTRACTION = "extraction"
    CODING = "coding"
    REASONING = "reasoning"
    DOCUMENT_ANALYSIS = "document_analysis"
    FINANCIAL_ANALYSIS = "financial_analysis"
    CUSTOMER_SUPPORT = "customer_support"
    CREATIVE_GENERATION = "creative_generation"
    CONVERSATION = "conversation"
    GENERAL_QA = "general_qa"
    DATA_ANALYSIS = "data_analysis"

class ComplexityLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"

class SensitivityLevel(str, Enum):
    PUBLIC = "PUBLIC"
    INTERNAL = "INTERNAL"
    CONFIDENTIAL = "CONFIDENTIAL"
    RESTRICTED = "RESTRICTED"

class CriticalityLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class PriorityLevel(str, Enum):
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

# ============================================================================
# Structured Analysis Result Schema
# ============================================================================
class AnalysisResult(BaseModel):
    intent: str = Field(..., description="Concise inferred user objective")
    task_type: TaskType = Field(..., description="Categorized NLP/LLM task")
    complexity: ComplexityLevel = Field(..., description="LOW, MEDIUM, or HIGH")
    estimated_input_tokens: int = Field(..., description="Estimated prompt token volume")
    estimated_output_tokens: int = Field(..., description="Estimated expected completion token volume")
    sensitivity: SensitivityLevel = Field(..., description="Data confidentiality classification")
    business_criticality: CriticalityLevel = Field(..., description="Impact on enterprise operations")
    required_quality: float = Field(..., description="Target quality benchmark score (0.0 - 100.0)")
    latency_requirement: str = Field(..., description="SLA tier: REALTIME, INTERACTIVE, or BATCH/DEEP")
    context_size: str = Field(..., description="Context volume category (SHORT, MEDIUM, LONG)")
    risk_level: RiskLevel = Field(..., description="Financial/operational risk exposure")
    priority: PriorityLevel = Field(..., description="Routing dispatch priority")

# ============================================================================
# Request Analyzer Engine
# ============================================================================
class RequestAnalyzer:
    """
    Deterministic rule-based Request Analyzer for NEXUS AI FINOPS.
    Extracts semantic intent, complexity, sensitivity, business criticality,
    expected token requirements, and SLA latency targets.
    """

    # Ordered priority list of task type detectors
    ORDERED_TASK_CHECKS = [
        # Explicit imperative action verbs
        (TaskType.TRANSLATION, [
            r"\btranslate\b", r"\btranslation\b", r"\binto (tamil|spanish|french|german|hindi|japanese|chinese|arabic|russian|italian|korean|portuguese)\b",
            r"\bfrom (english|tamil|spanish|french) to\b"
        ]),
        (TaskType.CONVERSATION, [
            r"^(how are you|hi\b|hello\b|hey\b|good (morning|afternoon|evening)|what's up|how's it going|how do you do|greetings)\b",
            r"\bhow are you doing\b", r"\bnice to meet you\b", r"\bwho are you\b"
        ]),
        (TaskType.EXTRACTION, [
            r"\bextract\b", r"\bparse\b", r"\bpull out\b", r"\bentity extraction\b",
            r"\bfind all entities\b", r"\bextract all\b", r"\bregex\b", r"\bscrape\b"
        ]),
        (TaskType.CLASSIFICATION, [
            r"\bclassif(y|ication)\b", r"\bcategoriz(e|ation)\b", r"\bsentiment\b",
            r"\blabel\b", r"\bwhich category\b", r"\btag this\b"
        ]),
        (TaskType.DOCUMENT_ANALYSIS, [
            r"\bcontract\b", r"\bindemnif(y|ication)\b", r"\bclause\b", r"\bnon-compete\b",
            r"\b40-page\b", r"\bagreement\b", r"\blegal document\b", r"\bterms of service\b",
            r"\bnda\b", r"\bmaster services agreement\b", r"\bcompliance policy\b", r"\breview this document\b"
        ]),
        (TaskType.DATA_ANALYSIS, [
            r"\bdata analysis\b", r"\banalyze dataset\b", r"\bstatistical analysis\b",
            r"\bscatter plot\b", r"\bcorrelation\b", r"\bpandas\b", r"\bdataframe\b"
        ]),
        (TaskType.FINANCIAL_ANALYSIS, [
            r"\bfinancial report\b", r"\bfraud\b", r"\bebitda\b", r"\bbalance sheet\b", r"\bp&l\b",
            r"\breconcil(e|iation)\b", r"\bsec 10-k\b", r"\baudit\b", r"\btax deduction\b",
            r"\bvariance\b", r"\bexpense anomaly\b", r"\bcapex\b", r"\bopex\b", r"\brevenue forecast\b", r"\bfinancial\b"
        ]),
        (TaskType.REASONING, [
            r"\bmathematical proof\b", r"\bmulti-step\b", r"\bprove that\b", r"\bproof\b",
            r"\blogic puzzle\b", r"\bdeduce\b", r"\btheorem\b", r"\bif and only if\b",
            r"\bformal logic\b", r"\bgame theory\b", r"\bchain of thought\b"
        ]),
        (TaskType.CODING, [
            r"\bcode\b", r"\bfunction\b", r"\brust\b", r"\bpython\b", r"\btypescript\b",
            r"\bjavascript\b", r"\bgolang\b", r"\braft\b", r"\btokio\b", r"\bdistributed lock\b",
            r"\brefactor\b", r"\bdebug\b", r"\bsql\b", r"\bapi\b", r"\bconcurrency\b",
            r"\bunit test\b", r"\balgorithm\b", r"\bcompiler\b", r"\bkubernetes\b", r"\bdocker\b"
        ]),
        (TaskType.CUSTOMER_SUPPORT, [
            r"\bcustomer support\b", r"\bticket\b", r"\bcustomer asking\b", r"\breset password\b",
            r"\btwo-factor\b", r"\b2fa\b", r"\brefund\b", r"\bhow do i\b", r"\bhelp desk\b"
        ]),
        (TaskType.CREATIVE_GENERATION, [
            r"\bstory\b", r"\bpoem\b", r"\bcreative\b", r"\bfuturistic\b",
            r"\bbrainstorm\b", r"\bslogan\b", r"\bscreenplay\b", r"\bfiction\b"
        ]),
        (TaskType.SUMMARIZATION, [
            r"\bsummariz(e|ation)\b", r"\bsummary\b", r"\btldr\b", r"\bdigest\b",
            r"\bbrief synopsis\b", r"\bexecutive summary\b", r"\bkey takeaways\b", r"\bcondense\b"
        ]),
        (TaskType.GENERAL_QA, [
            r"\b(explain|what is|what are|how does|why does|tell me about|define|meaning of|concept of)\b",
            r"\bgive me an overview of\b", r"\bdescribe\b"
        ])
    ]

    @classmethod
    def estimate_tokens(cls, text: str) -> int:
        if not text:
            return 0
        words = text.split()
        special_chars = len(re.findall(r"[{}\[\](),;:+\-*\/=<>_\"']", text))
        return max(1, int((len(words) * 1.33) + (special_chars * 0.35)))

    @classmethod
    def analyze(cls, prompt: str, context: Optional[str] = None) -> AnalysisResult:
        """
        Analyzes a prompt using deterministic rules.
        """
        clean_prompt = prompt.strip()
        p_lower = clean_prompt.lower()
        full_text = f"{clean_prompt} {context or ''}".strip()
        input_tokens = cls.estimate_tokens(full_text)

        # 1. Determine Task Type
        task_type = cls._detect_task_type(p_lower)

        # 2. Determine Complexity
        complexity = cls._detect_complexity(p_lower, task_type, input_tokens)

        # 3. Determine Estimated Output Tokens based on Task and Complexity
        output_tokens = cls._estimate_output_tokens(task_type, complexity, input_tokens)

        # 4. Determine Sensitivity
        sensitivity = cls._detect_sensitivity(p_lower, task_type)

        # 5. Determine Business Criticality
        criticality = cls._detect_criticality(p_lower, task_type, complexity, sensitivity)

        # 6. Determine Priority
        priority = cls._detect_priority(p_lower, criticality)

        # 7. Determine Quality Benchmark Requirement (0 - 100)
        required_quality = cls._detect_required_quality(complexity, criticality)

        # 8. Determine Latency Requirement
        latency_requirement = cls._detect_latency_requirement(task_type, complexity)

        # 9. Determine Context Size Category
        context_size = cls._detect_context_size(input_tokens)

        # 10. Determine Risk Level
        risk_level = cls._detect_risk_level(sensitivity, criticality)

        # 11. Generate Inferred Intent Description
        intent = cls._synthesize_intent(clean_prompt, task_type)

        return AnalysisResult(
            intent=intent,
            task_type=task_type,
            complexity=complexity,
            estimated_input_tokens=input_tokens,
            estimated_output_tokens=output_tokens,
            sensitivity=sensitivity,
            business_criticality=criticality,
            required_quality=required_quality,
            latency_requirement=latency_requirement,
            context_size=context_size,
            risk_level=risk_level,
            priority=priority
        )

    @classmethod
    def _detect_task_type(cls, text: str) -> TaskType:
        # Check high-specificity patterns in priority order
        for t_type, patterns in cls.ORDERED_TASK_CHECKS:
            for pat in patterns:
                if re.search(pat, text):
                    return t_type
        return TaskType.GENERAL_QA

    @classmethod
    def _detect_complexity(cls, text: str, task_type: TaskType, tokens: int) -> ComplexityLevel:
        # Rule 1: High complexity keywords or tasks
        high_indicators = [
            "fraud", "distributed", "raft", "tokio", "concurrency", "lock manager",
            "proof", "multi-step", "mathematical proof", "40-page", "indemnif",
            "monte carlo", "complex", "architecture", "deep reasoning", "theorem"
        ]
        if any(ind in text for ind in high_indicators):
            return ComplexityLevel.HIGH

        if task_type in [TaskType.FINANCIAL_ANALYSIS, TaskType.REASONING] and ("audit" in text or "risk" in text or "proof" in text):
            return ComplexityLevel.HIGH

        if task_type == TaskType.CODING and ("rust" in text or "consensus" in text or "distributed" in text or "lock" in text):
            return ComplexityLevel.HIGH

        if task_type == TaskType.DOCUMENT_ANALYSIS and ("contract" in text or "agreement" in text or "clause" in text):
            return ComplexityLevel.HIGH

        # Rule 2: Low complexity tasks and conversational / simple QA prompts
        if task_type == TaskType.CONVERSATION:
            return ComplexityLevel.LOW

        if task_type == TaskType.GENERAL_QA and any(w in text for w in ["simple terms", "explain simply", "in simple terms", "for beginners", "simply", "basic"]):
            return ComplexityLevel.LOW

        low_indicators = [
            task_type == TaskType.TRANSLATION and tokens < 100,
            task_type == TaskType.CLASSIFICATION and tokens < 150,
            task_type == TaskType.CUSTOMER_SUPPORT and ("reset" in text or "how do i" in text) and tokens < 80,
            "translate this sentence" in text,
            any(w in text for w in ["simple terms", "explain simply", "in simple terms", "for beginners", "simply"]),
            tokens < 40 and task_type in [TaskType.TRANSLATION, TaskType.EXTRACTION],
            tokens < 80 and task_type in [TaskType.CONVERSATION, TaskType.GENERAL_QA]
        ]
        if any(low_indicators):
            return ComplexityLevel.LOW

        # Rule 3: Medium complexity by default for standard summarization and drafting
        if task_type == TaskType.SUMMARIZATION or "summarize" in text:
            return ComplexityLevel.MEDIUM

        if tokens > 1000:
            return ComplexityLevel.HIGH
        elif tokens < 80:
            return ComplexityLevel.LOW
        else:
            return ComplexityLevel.MEDIUM

    @classmethod
    def _estimate_output_tokens(cls, task_type: TaskType, complexity: ComplexityLevel, input_tokens: int) -> int:
        if task_type == TaskType.CLASSIFICATION:
            return 15
        elif task_type == TaskType.CONVERSATION:
            return 60
        elif task_type == TaskType.TRANSLATION:
            return max(20, int(input_tokens * 1.1))
        elif task_type == TaskType.EXTRACTION:
            return max(50, int(input_tokens * 0.35))
        elif task_type == TaskType.SUMMARIZATION:
            return max(80, int(input_tokens * 0.25))
        elif task_type == TaskType.GENERAL_QA:
            return 180 if complexity == ComplexityLevel.LOW else 350
        elif task_type == TaskType.DATA_ANALYSIS:
            return 300
        elif task_type == TaskType.CUSTOMER_SUPPORT:
            return 120
        elif task_type == TaskType.CODING:
            return 450 if complexity == ComplexityLevel.HIGH else 200
        elif task_type in [TaskType.FINANCIAL_ANALYSIS, TaskType.DOCUMENT_ANALYSIS, TaskType.REASONING]:
            return 550 if complexity == ComplexityLevel.HIGH else 250
        elif task_type == TaskType.CREATIVE_GENERATION:
            return 400
        return 200

    @classmethod
    def _detect_sensitivity(cls, text: str, task_type: TaskType) -> SensitivityLevel:
        if any(w in text for w in ["fraud", "ssn", "credit card", "bank", "password", "2fa", "two-factor", "restricted", "insider", "subpoena"]):
            return SensitivityLevel.RESTRICTED
        if task_type == TaskType.FINANCIAL_ANALYSIS or any(w in text for w in ["financial report", "invoice", "audit", "contract", "confidential", "salary", "balance sheet"]):
            return SensitivityLevel.CONFIDENTIAL
        if task_type in [TaskType.DOCUMENT_ANALYSIS, TaskType.CUSTOMER_SUPPORT] or any(w in text for w in ["internal", "ticket", "employee", "handbook", "policy"]):
            return SensitivityLevel.INTERNAL
        return SensitivityLevel.PUBLIC

    @classmethod
    def _detect_criticality(cls, text: str, task_type: TaskType, complexity: ComplexityLevel, sensitivity: SensitivityLevel) -> CriticalityLevel:
        if "fraud" in text or "production down" in text or "security breach" in text:
            return CriticalityLevel.CRITICAL
        if task_type == TaskType.FINANCIAL_ANALYSIS and ("fraud" in text or "audit" in text or "report" in text):
            return CriticalityLevel.HIGH
        if task_type == TaskType.DOCUMENT_ANALYSIS and "indemnif" in text:
            return CriticalityLevel.HIGH
        if complexity == ComplexityLevel.HIGH:
            return CriticalityLevel.HIGH
        if task_type in [TaskType.CONVERSATION, TaskType.GENERAL_QA] and complexity == ComplexityLevel.LOW:
            return CriticalityLevel.LOW
        if task_type in [TaskType.SUMMARIZATION, TaskType.CODING, TaskType.CUSTOMER_SUPPORT]:
            return CriticalityLevel.MEDIUM
        return CriticalityLevel.LOW

    @classmethod
    def _detect_priority(cls, text: str, criticality: CriticalityLevel) -> PriorityLevel:
        if criticality == CriticalityLevel.CRITICAL or any(w in text for w in ["urgent", "emergency", "asap", "immediate", "production down"]):
            return PriorityLevel.CRITICAL
        if criticality == CriticalityLevel.HIGH or "fraud" in text:
            return PriorityLevel.HIGH
        if criticality == CriticalityLevel.MEDIUM:
            return PriorityLevel.NORMAL
        return PriorityLevel.LOW

    @classmethod
    def _detect_required_quality(cls, complexity: ComplexityLevel, criticality: CriticalityLevel) -> float:
        if criticality == CriticalityLevel.CRITICAL or complexity == ComplexityLevel.HIGH:
            return 97.0
        elif complexity == ComplexityLevel.MEDIUM or criticality == CriticalityLevel.HIGH:
            return 91.0
        else:
            return 82.0

    @classmethod
    def _detect_latency_requirement(cls, task_type: TaskType, complexity: ComplexityLevel) -> str:
        if task_type in [TaskType.CUSTOMER_SUPPORT, TaskType.TRANSLATION, TaskType.CLASSIFICATION, TaskType.CONVERSATION] and complexity == ComplexityLevel.LOW:
            return "REALTIME (< 500ms)"
        elif complexity == ComplexityLevel.HIGH or task_type in [TaskType.FINANCIAL_ANALYSIS, TaskType.DOCUMENT_ANALYSIS, TaskType.REASONING]:
            return "DEEP_ANALYSIS (< 5000ms)"
        else:
            return "INTERACTIVE (< 1500ms)"

    @classmethod
    def _detect_context_size(cls, input_tokens: int) -> str:
        if input_tokens > 2000:
            return f"LONG ({input_tokens} tokens)"
        elif input_tokens > 500:
            return f"MEDIUM ({input_tokens} tokens)"
        else:
            return f"SHORT ({input_tokens} tokens)"

    @classmethod
    def _detect_risk_level(cls, sensitivity: SensitivityLevel, criticality: CriticalityLevel) -> RiskLevel:
        if sensitivity == SensitivityLevel.RESTRICTED or criticality == CriticalityLevel.CRITICAL:
            return RiskLevel.CRITICAL
        elif sensitivity == SensitivityLevel.CONFIDENTIAL or criticality == CriticalityLevel.HIGH:
            return RiskLevel.HIGH
        elif sensitivity == SensitivityLevel.INTERNAL:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW

    @classmethod
    def _synthesize_intent(cls, prompt: str, task_type: TaskType) -> str:
        first_sentence = prompt.split(".")[0].strip()
        if len(first_sentence) <= 60:
            return first_sentence
        return f"{task_type.value.replace('_', ' ').title()}: {first_sentence[:55]}..."
