import sys
from pathlib import Path
import pytest

# Add backend directory to sys.path
backend_path = Path(__file__).resolve().parent.parent / "backend"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from app.core.analyzer import (
    RequestAnalyzer,
    AnalysisResult,
    TaskType,
    ComplexityLevel,
    SensitivityLevel,
    CriticalityLevel,
    PriorityLevel,
    RiskLevel
)

# ============================================================================
# 10 Test Case Prompts Covering All Specification Task Types and Edge Cases
# ============================================================================
TEST_CASES = [
    # 1. Translation (Low complexity example from prompt)
    {
        "id": "TC_01_TRANSLATION",
        "prompt": "Translate this sentence into Tamil.",
        "expected_task": TaskType.TRANSLATION,
        "expected_complexity": ComplexityLevel.LOW,
        "expected_sensitivity": SensitivityLevel.PUBLIC,
        "expected_criticality": CriticalityLevel.LOW,
        "expected_priority": PriorityLevel.LOW,
    },
    # 2. Summarization (Medium complexity example from prompt)
    {
        "id": "TC_02_SUMMARIZATION",
        "prompt": "Summarize this document.",
        "expected_task": TaskType.SUMMARIZATION,
        "expected_complexity": ComplexityLevel.MEDIUM,
        "expected_criticality": CriticalityLevel.MEDIUM,
    },
    # 3. Financial Analysis with Fraud (High complexity & Criticality example from prompt)
    {
        "id": "TC_03_FINANCIAL_FRAUD",
        "prompt": "Analyze this financial report and identify fraud risks.",
        "expected_task": TaskType.FINANCIAL_ANALYSIS,
        "expected_complexity": ComplexityLevel.HIGH,
        "expected_criticality": CriticalityLevel.CRITICAL,
        "expected_sensitivity": SensitivityLevel.RESTRICTED,
        "expected_priority": PriorityLevel.CRITICAL,
    },
    # 4. Complex Coding (High complexity example from prompt)
    {
        "id": "TC_04_COMPLEX_CODING",
        "prompt": "Write a high-performance distributed lock manager in Rust with Tokio and Raft consensus.",
        "expected_task": TaskType.CODING,
        "expected_complexity": ComplexityLevel.HIGH,
        "expected_criticality": CriticalityLevel.HIGH,
    },
    # 5. Complex Reasoning (High complexity example from prompt)
    {
        "id": "TC_05_REASONING_PROOF",
        "prompt": "Solve this multi-step mathematical proof: prove that if A implies B and B implies C, then A implies C.",
        "expected_task": TaskType.REASONING,
        "expected_complexity": ComplexityLevel.HIGH,
        "expected_criticality": CriticalityLevel.HIGH,
    },
    # 6. Classification
    {
        "id": "TC_06_CLASSIFICATION",
        "prompt": "Classify this customer ticket into billing, technical, or cancellation: 'I want a refund for my charged card'.",
        "expected_task": TaskType.CLASSIFICATION,
        "expected_complexity": ComplexityLevel.LOW,
    },
    # 7. Extraction
    {
        "id": "TC_07_EXTRACTION",
        "prompt": "Extract all invoice line items, dates, vendor names, and tax deduction values from this text.",
        "expected_task": TaskType.EXTRACTION,
    },
    # 8. Document Analysis (Contract / Indemnification)
    {
        "id": "TC_08_DOCUMENT_ANALYSIS",
        "prompt": "Review this 40-page contract agreement and identify all non-compete indemnification clauses.",
        "expected_task": TaskType.DOCUMENT_ANALYSIS,
        "expected_complexity": ComplexityLevel.HIGH,
        "expected_sensitivity": SensitivityLevel.CONFIDENTIAL,
        "expected_criticality": CriticalityLevel.HIGH,
    },
    # 9. Customer Support (2FA / Security)
    {
        "id": "TC_09_CUSTOMER_SUPPORT",
        "prompt": "Respond to a customer asking how to reset their two-factor authentication password.",
        "expected_task": TaskType.CUSTOMER_SUPPORT,
        "expected_sensitivity": SensitivityLevel.RESTRICTED,
    },
    # 10. Creative Generation
    {
        "id": "TC_10_CREATIVE_STORY",
        "prompt": "Write an inspiring futuristic story about an autonomous colony exploring Europa.",
        "expected_task": TaskType.CREATIVE_GENERATION,
        "expected_sensitivity": SensitivityLevel.PUBLIC,
        "expected_criticality": CriticalityLevel.LOW,
        "expected_priority": PriorityLevel.LOW,
    }
]

@pytest.mark.parametrize("case", TEST_CASES, ids=lambda c: c["id"])
def test_request_analyzer_test_cases(case):
    """
    Test RequestAnalyzer on all 10 required prompt scenarios,
    validating task_type, complexity, tokens, sensitivity, criticality, quality, and priority.
    """
    res: AnalysisResult = RequestAnalyzer.analyze(case["prompt"])

    # 1. Check task_type
    assert res.task_type == case["expected_task"], (
        f"For '{case['prompt']}', expected task {case['expected_task']}, got {res.task_type}"
    )

    # 2. Check complexity if specified
    if "expected_complexity" in case:
        assert res.complexity == case["expected_complexity"], (
            f"For '{case['prompt']}', expected complexity {case['expected_complexity']}, got {res.complexity}"
        )

    # 3. Check criticality if specified
    if "expected_criticality" in case:
        assert res.business_criticality == case["expected_criticality"], (
            f"For '{case['prompt']}', expected criticality {case['expected_criticality']}, got {res.business_criticality}"
        )

    # 4. Check sensitivity if specified
    if "expected_sensitivity" in case:
        assert res.sensitivity == case["expected_sensitivity"], (
            f"For '{case['prompt']}', expected sensitivity {case['expected_sensitivity']}, got {res.sensitivity}"
        )

    # 5. Check priority if specified
    if "expected_priority" in case:
        assert res.priority == case["expected_priority"], (
            f"For '{case['prompt']}', expected priority {case['expected_priority']}, got {res.priority}"
        )

    # 6. Check common schema integrity across all 10 requests
    assert len(res.intent) > 0
    assert res.estimated_input_tokens > 0
    assert res.estimated_output_tokens > 0
    assert 0.0 <= res.required_quality <= 100.0
    assert res.risk_level in [RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL]
    assert len(res.latency_requirement) > 0
    assert len(res.context_size) > 0

def test_prompt_specification_exact_examples():
    """
    Verifies the exact examples highlighted in the prompt:
    1. 'Translate this sentence into Tamil.' -> translation, LOW
    2. 'Summarize this document.' -> summarization, MEDIUM
    3. 'Analyze this financial report and identify fraud risks.' -> financial_analysis, HIGH, HIGH/CRITICAL criticality
    4. Complex coding/reasoning -> HIGH
    """
    ex1 = RequestAnalyzer.analyze("Translate this sentence into Tamil.")
    assert ex1.task_type == TaskType.TRANSLATION
    assert ex1.complexity == ComplexityLevel.LOW

    ex2 = RequestAnalyzer.analyze("Summarize this document.")
    assert ex2.task_type == TaskType.SUMMARIZATION
    assert ex2.complexity == ComplexityLevel.MEDIUM

    ex3 = RequestAnalyzer.analyze("Analyze this financial report and identify fraud risks.")
    assert ex3.task_type == TaskType.FINANCIAL_ANALYSIS
    assert ex3.complexity == ComplexityLevel.HIGH
    assert ex3.business_criticality in [CriticalityLevel.HIGH, CriticalityLevel.CRITICAL]

    ex4_code = RequestAnalyzer.analyze("Write a high-performance distributed lock manager in Rust with Tokio and Raft consensus.")
    assert ex4_code.task_type == TaskType.CODING
    assert ex4_code.complexity == ComplexityLevel.HIGH

    ex4_reasoning = RequestAnalyzer.analyze("Solve this multi-step mathematical proof: prove theorem using formal logic.")
    assert ex4_reasoning.task_type == TaskType.REASONING
    assert ex4_reasoning.complexity == ComplexityLevel.HIGH

def test_api_analyze_endpoint():
    """
    Test POST /api/v1/analyze FastAPI endpoint returns full AnalysisResult.
    """
    # Directly call the route handler function
    from main import analyze_request, PromptAnalysisRequest
    req = PromptAnalysisRequest(prompt="Analyze this financial report and identify fraud risks.")
    res = analyze_request(req)
    assert res.task_type == TaskType.FINANCIAL_ANALYSIS
    assert res.complexity == ComplexityLevel.HIGH
    assert res.business_criticality == CriticalityLevel.CRITICAL
    assert res.sensitivity == SensitivityLevel.RESTRICTED
    assert res.risk_level == RiskLevel.CRITICAL
    assert res.priority == PriorityLevel.CRITICAL
    assert res.estimated_input_tokens > 0
    assert res.estimated_output_tokens > 0