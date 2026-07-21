CATEGORY_KEYWORDS = {
    "Invoice": ["invoice", "bill to", "amount due", "payment receipt", "purchase order"],
    "Resume": ["curriculum vitae", "resume", "work experience", "professional summary"],
    "Certificate": ["certificate of completion", "certified", "has successfully completed"],
    "Contract": ["agreement", "terms and conditions", "party of the first part", "hereby agree"],
    "Report": ["executive summary", "quarterly report", "annual report", "findings"],
}


def classify(text):
    if not text:
        return "Unsorted"
    lowered = text.lower()
    scores = {}
    for category, keywords in CATEGORY_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in lowered)
        if score > 0:
            scores[category] = score
    if not scores:
        return "Unsorted"
    return max(scores, key=scores.get)