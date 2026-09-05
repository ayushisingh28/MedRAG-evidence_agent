import re

EMERGENCY_PATTERNS = (
    r"chest pain",
    r"can'?t breathe|difficulty breathing|shortness of breath",
    r"suicid|self.?harm",
    r"stroke|face droop|slurred speech",
    r"overdose|poison",
    r"unconscious|passed out",
)
PERSONAL_TREATMENT_PATTERNS = (
    r"what (dose|dosage) (should|can) i",
    r"should i (take|stop|start)",
    r"diagnose me|do i have",
    r"my (symptoms|child|pregnan|medication)",
)


def safety_status(question: str) -> str | None:
    normalized = question.lower()
    if any(re.search(pattern, normalized) for pattern in EMERGENCY_PATTERNS):
        return "emergency"
    if any(re.search(pattern, normalized) for pattern in PERSONAL_TREATMENT_PATTERNS):
        return "clinical_review"
    return None
