CATEGORY_KEYWORDS = {
    "Invoice": {
        "strong": ["invoice number", "tax invoice", "bill to", "amount due"],
        "weak": ["invoice", "payment receipt", "purchase order", "subtotal"],
        "exclude": [],
    },
    "Resume": {
        "strong": ["curriculum vitae", "career objective", "professional summary"],
        "weak": ["resume", "work experience", "education", "skills"],
        "exclude": ["syllabus", "semester", "credits", "unit 1", "university"],
    },
    "Certificate": {
        "strong": ["certificate of completion", "has successfully completed", "this is to certify"],
        "weak": ["certified", "certificate"],
        "exclude": ["syllabus", "semester", "credits", "unit 1", "university"],
    },
    "Contract": {
        "strong": ["party of the first part", "hereby agree", "terms and conditions"],
        "weak": ["agreement", "contract"],
        "exclude": [],
    },
    "Report": {
        "strong": ["executive summary", "quarterly report", "annual report"],
        "weak": ["findings", "report"],
        "exclude": [],
    },
    "Offer Letter": {
        "strong": ["offer letter", "we are pleased to offer", "letter of appointment", "your date of joining"],
        "weak": ["appointment letter", "joining date", "ctc"],
        "exclude": [],
    },
}

STRONG_WEIGHT = 3
WEAK_WEIGHT = 1
QUALIFY_THRESHOLD = 3


def classify(text):
    if not text:
        return "Unsorted"
    lowered = text.lower()
    scores = {}
    for category, keyword_groups in CATEGORY_KEYWORDS.items():
        if any(ex in lowered for ex in keyword_groups.get("exclude", [])):
            continue
        score = 0
        score += sum(STRONG_WEIGHT for kw in keyword_groups["strong"] if kw in lowered)
        score += sum(WEAK_WEIGHT for kw in keyword_groups["weak"] if kw in lowered)
        if score >= QUALIFY_THRESHOLD:
            scores[category] = score
    if not scores:
        return "Unsorted"
    return max(scores, key=scores.get)