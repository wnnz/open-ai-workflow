import json
import re
from typing import Any

from fastapi import HTTPException, status


def first_non_null(values: list[Any]) -> Any:
    return next((value for value in values if value is not None), None)


def empty_assignment_value(value_type: str) -> Any:
    return {"String": "", "Number": 0, "Boolean": False, "Object": {}, "Array": []}.get(
        value_type
    )


def coerce_assignment_value(value: Any, value_type: str) -> Any:
    if value_type == "Any" or value is None:
        return value
    if value_type == "String":
        if isinstance(value, str):
            return value
        return json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else str(value)
    if value_type == "Number":
        try:
            number = float(value)
            return int(number) if number.is_integer() else number
        except (TypeError, ValueError) as exc:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_CONTENT, "Variable value is not a number"
            ) from exc
    if value_type == "Boolean":
        if isinstance(value, bool):
            return value
        normalized = str(value).strip().casefold()
        if normalized in {"true", "1", "yes", "on"}:
            return True
        if normalized in {"false", "0", "no", "off", ""}:
            return False
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, "Variable value is not a boolean"
        )
    if value_type in {"Object", "Array"}:
        parsed = json.loads(value) if isinstance(value, str) else value
        expected = dict if value_type == "Object" else list
        if not isinstance(parsed, expected):
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                f"Variable value is not an {value_type.lower()}",
            )
        return parsed
    return value


def read_object_path(value: Any, path: str) -> Any:
    current = value
    for part in filter(None, path.split(".")):
        if isinstance(current, dict):
            current = current.get(part)
        elif isinstance(current, list) and part.isdigit() and int(part) < len(current):
            current = current[int(part)]
        else:
            return None
    return current


def evaluate_condition_clause(clause: dict[str, Any]) -> bool:
    left, right, operator = clause.get("variable"), clause.get("value"), clause.get("operator")
    if operator == "is_empty":
        return left in (None, "", [], {})
    if operator == "is_not_empty":
        return left not in (None, "", [], {})
    if operator == "equals":
        return left == right or str(left) == str(right)
    if operator == "not_equals":
        return not evaluate_condition_clause({**clause, "operator": "equals"})
    if operator in {"contains", "not_contains"}:
        contained = right in left if isinstance(left, (list, tuple, set, dict)) else str(right) in str(left or "")
        return not contained if operator == "not_contains" else contained
    if operator == "starts_with":
        return str(left or "").startswith(str(right))
    if operator == "ends_with":
        return str(left or "").endswith(str(right))
    if operator == "in":
        choices = right if isinstance(right, list) else [item.strip() for item in str(right).split(",")]
        return left in choices or str(left) in {str(item) for item in choices}
    try:
        left_number, right_number = float(left), float(right)
    except (TypeError, ValueError):
        return False
    return {
        "greater_than": left_number > right_number,
        "less_than": left_number < right_number,
        "greater_or_equal": left_number >= right_number,
        "less_or_equal": left_number <= right_number,
    }.get(str(operator), False)


def list_item_matches(item: Any, filter_config: dict[str, Any]) -> bool:
    field = str(filter_config.get("field", "")).strip()
    left = read_object_path(item, field) if field else item
    return evaluate_condition_clause(
        {
            "variable": left,
            "operator": filter_config.get("operator", "equals"),
            "value": filter_config.get("value"),
        }
    )


def sortable_value(value: Any) -> tuple[int, Any]:
    if value is None:
        return (2, "")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return (0, value)
    if isinstance(value, (dict, list)):
        return (1, json.dumps(value, ensure_ascii=False, sort_keys=True))
    return (1, str(value).casefold())


def stable_item_key(value: Any) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    except (TypeError, ValueError):
        return repr(value)


def extract_structured_parameters(config: dict[str, Any]) -> dict[str, Any]:
    source = config.get("source")
    parsed: dict[str, Any] = source if isinstance(source, dict) else {}
    if isinstance(source, str):
        try:
            candidate = json.loads(source)
            if isinstance(candidate, dict):
                parsed = candidate
        except json.JSONDecodeError:
            parsed = {}
    output: dict[str, Any] = {}
    for field in config.get("fields", []):
        name = str(field.get("name", ""))
        value = read_object_path(parsed, name) if parsed else None
        if value is None and isinstance(source, str):
            match = re.search(rf"(?im)^\s*{re.escape(name)}\s*[:=：]\s*(.+?)\s*$", source)
            value = match.group(1) if match else None
        output[name] = (
            coerce_assignment_value(value, field.get("type", "String"))
            if value is not None
            else None
        )
    return output


def evaluate_condition(config: dict[str, Any]) -> dict[str, Any]:
    conditions = config.get("conditions")
    if isinstance(conditions, list) and conditions:
        results = [evaluate_condition_clause(clause) for clause in conditions]
        result = any(results) if config.get("logical_operator", "and") == "or" else all(results)
        return {"result": result, "branch": "true" if result else "false", "clauses": results}
    result = evaluate_legacy_condition(config.get("expression"))
    return {"result": result, "branch": "true" if result else "false", "clauses": [result]}


def evaluate_classifier(config: dict[str, Any]) -> dict[str, Any]:
    source = str(config.get("input") or "").strip()
    normalized_source = source.casefold()
    categories = config.get("categories", [])
    best_category: dict[str, Any] | None = None
    best_score = 0
    matched_terms: list[str] = []
    for category in categories:
        name = str(category.get("name") or "").strip()
        description_terms = [
            term.strip()
            for term in re.split(r"[,，;；。.!！?？\s]+", str(category.get("description") or ""))
            if len(term.strip()) >= 2
        ]
        terms = [name, *category.get("keywords", []), *description_terms]
        matches = [term for term in terms if term and term.casefold() in normalized_source]
        exact = bool(name and name.casefold() == normalized_source)
        score = (1000 if exact else 0) + sum(max(1, len(term)) for term in matches)
        if score > best_score:
            best_category, best_score, matched_terms = category, score, matches
    fallback = best_category is None
    if fallback:
        best_category = categories[-1]
    category_id = str(best_category["id"])
    return {
        "class_id": category_id,
        "class_name": str(best_category["name"]),
        "branch": f"category:{category_id}",
        "confidence": 0.0
        if fallback
        else min(1.0, best_score / 1000 if best_score >= 1000 else best_score / 20),
        "matched_terms": matched_terms,
        "fallback": fallback,
    }


def evaluate_legacy_condition(expression: Any) -> bool:
    if isinstance(expression, bool):
        return expression
    text = str(expression or "").strip()
    if text.lower() in {"true", "yes", "1"}:
        return True
    if text.lower() in {"false", "no", "0", "", "none", "null"}:
        return False
    match = re.fullmatch(r"\s*(.*?)\s*(==|!=|>=|<=|>|<)\s*(.*?)\s*", text)
    if not match:
        return bool(text)
    left, operator, right = match.groups()
    left, right = parse_condition_literal(left), parse_condition_literal(right)
    if operator == "==":
        return left == right or str(left) == str(right)
    if operator == "!=":
        return not (left == right or str(left) == str(right))
    try:
        left, right = float(left), float(right)
    except (TypeError, ValueError):
        return False
    return {">": left > right, "<": left < right, ">=": left >= right, "<=": left <= right}[
        operator
    ]


def parse_condition_literal(value: str) -> Any:
    stripped = value.strip()
    try:
        return json.loads(
            stripped.lower() if stripped.lower() in {"true", "false", "null"} else stripped
        )
    except json.JSONDecodeError:
        return stripped.strip("'\"")
