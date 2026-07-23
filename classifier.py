from pathlib import Path
import sys

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

if getattr(sys, "frozen", False):
    _BASE_DIR = Path(sys.executable).parent
else:
    _BASE_DIR = Path(__file__).parent

CONFIG_PATH = _BASE_DIR / "config.yaml"

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


CONFIG_HEADER_COMMENT = """# PDF Bulk Organizer — category configuration
#
# Edit this file (or use the in-app Category Editor) to add, remove, or tune
# categories without touching any code.
#
# Each category has three keyword lists:
#   strong  — near-certain identifiers (worth more points, e.g. "invoice number")
#   weak    — supporting signals (worth fewer points, e.g. "invoice")
#   exclude — if ANY of these appear, this category is vetoed entirely
#
# scoring:
#   strong_weight     — points awarded per strong keyword match
#   weak_weight       — points awarded per weak keyword match
#   qualify_threshold — a category must reach this score to be selected
"""


def get_current_config():
    return {
        "categories": {
            name: {
                "strong": list(group.get("strong", [])),
                "weak": list(group.get("weak", [])),
                "exclude": list(group.get("exclude", [])),
            }
            for name, group in _state["category_keywords"].items()
        },
        "scoring": dict(_state["scoring"]),
    }


def write_config(categories, scoring, config_path=None):
    if not YAML_AVAILABLE:
        return False, "PyYAML is not installed — run: pip install pyyaml"

    path = Path(config_path) if config_path else CONFIG_PATH

    if not isinstance(categories, dict) or not categories:
        return False, "At least one category is required."

    cleaned_categories = {}
    for name, group in categories.items():
        clean_name = str(name).strip()
        if not clean_name:
            return False, "Category names cannot be empty."
        cleaned_categories[clean_name] = {
            "strong": [str(k).strip().lower() for k in group.get("strong", []) if str(k).strip()],
            "weak": [str(k).strip().lower() for k in group.get("weak", []) if str(k).strip()],
            "exclude": [str(k).strip().lower() for k in group.get("exclude", []) if str(k).strip()],
        }

    try:
        strong_weight = int(scoring.get("strong_weight", DEFAULT_SCORING["strong_weight"]))
        weak_weight = int(scoring.get("weak_weight", DEFAULT_SCORING["weak_weight"]))
        qualify_threshold = int(scoring.get("qualify_threshold", DEFAULT_SCORING["qualify_threshold"]))
    except (TypeError, ValueError):
        return False, "Scoring values must be whole numbers."

    data = {
        "categories": cleaned_categories,
        "scoring": {
            "strong_weight": strong_weight,
            "weak_weight": weak_weight,
            "qualify_threshold": qualify_threshold,
        },
    }

    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(CONFIG_HEADER_COMMENT)
            f.write("\n")
            yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True)
    except Exception as exc:
        return False, f"Failed to write config.yaml: {exc}"

    reload_config(path)
    return True, None


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