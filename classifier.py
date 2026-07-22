from pathlib import Path

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

CONFIG_PATH = Path(__file__).parent / "config.yaml"

DEFAULT_CATEGORY_KEYWORDS = {
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

DEFAULT_SCORING = {
    "strong_weight": 3,
    "weak_weight": 1,
    "qualify_threshold": 3,
}

_state = {
    "category_keywords": DEFAULT_CATEGORY_KEYWORDS,
    "scoring": DEFAULT_SCORING,
    "source": "built-in defaults",
    "error": None,
}


def _validate_categories(raw_categories):
    if not isinstance(raw_categories, dict) or not raw_categories:
        raise ValueError("'categories' must be a non-empty mapping")
    cleaned = {}
    for name, group in raw_categories.items():
        if not isinstance(group, dict):
            raise ValueError(f"Category '{name}' must be a mapping with strong/weak/exclude lists")
        cleaned[name] = {
            "strong": [str(k).lower() for k in group.get("strong", []) or []],
            "weak": [str(k).lower() for k in group.get("weak", []) or []],
            "exclude": [str(k).lower() for k in group.get("exclude", []) or []],
        }
    return cleaned


def reload_config(config_path=None):
    path = Path(config_path) if config_path else CONFIG_PATH

    if not YAML_AVAILABLE:
        _state.update(
            category_keywords=DEFAULT_CATEGORY_KEYWORDS,
            scoring=DEFAULT_SCORING,
            source="built-in defaults (PyYAML not installed)",
            error="PyYAML is not installed — run: pip install pyyaml",
        )
        return _state

    if not path.exists():
        _state.update(
            category_keywords=DEFAULT_CATEGORY_KEYWORDS,
            scoring=DEFAULT_SCORING,
            source="built-in defaults (no config.yaml found)",
            error=None,
        )
        return _state

    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f)

        if not isinstance(raw, dict):
            raise ValueError("Top-level YAML content must be a mapping")

        category_keywords = _validate_categories(raw.get("categories", {}))

        scoring_raw = raw.get("scoring", {}) or {}
        scoring = {
            "strong_weight": int(scoring_raw.get("strong_weight", DEFAULT_SCORING["strong_weight"])),
            "weak_weight": int(scoring_raw.get("weak_weight", DEFAULT_SCORING["weak_weight"])),
            "qualify_threshold": int(scoring_raw.get("qualify_threshold", DEFAULT_SCORING["qualify_threshold"])),
        }

        _state.update(
            category_keywords=category_keywords,
            scoring=scoring,
            source=str(path),
            error=None,
        )

    except Exception as exc:
        _state.update(
            category_keywords=DEFAULT_CATEGORY_KEYWORDS,
            scoring=DEFAULT_SCORING,
            source="built-in defaults (config.yaml failed to load)",
            error=f"{type(exc).__name__}: {exc}",
        )

    return _state


def get_config_status():
    return {
        "source": _state["source"],
        "error": _state["error"],
        "category_count": len(_state["category_keywords"]),
    }


def classify(text):
    if not text:
        return "Unsorted"

    lowered = text.lower()
    category_keywords = _state["category_keywords"]
    scoring = _state["scoring"]

    scores = {}
    for category, keyword_groups in category_keywords.items():
        if any(ex in lowered for ex in keyword_groups.get("exclude", [])):
            continue
        score = 0
        score += sum(scoring["strong_weight"] for kw in keyword_groups["strong"] if kw in lowered)
        score += sum(scoring["weak_weight"] for kw in keyword_groups["weak"] if kw in lowered)
        if score >= scoring["qualify_threshold"]:
            scores[category] = score

    if not scores:
        return "Unsorted"
    return max(scores, key=scores.get)


reload_config()