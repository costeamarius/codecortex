"""Validation helpers for safe execution."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Callable, Dict

from .models import ValidationResult


ValidatorFn = Callable[[str, str], ValidationResult]


def validate_json(path: str, content: str) -> ValidationResult:
    try:
        json.loads(content)
        return ValidationResult(passed=True, validator="json")
    except json.JSONDecodeError as exc:
        return ValidationResult(passed=False, validator="json", errors=[str(exc)])


def validate_python(path: str, content: str) -> ValidationResult:
    try:
        compile(content, path, "exec")
        return ValidationResult(passed=True, validator="python_compile")
    except SyntaxError as exc:
        return ValidationResult(passed=False, validator="python_compile", errors=[str(exc)])


VALIDATOR_BY_EXTENSION: Dict[str, ValidatorFn] = {
    ".json": validate_json,
    ".py": validate_python,
}


def get_validator_for_path(path: str) -> ValidatorFn | None:
    return VALIDATOR_BY_EXTENSION.get(Path(path).suffix.lower())


def validate_content(path: str, content: str) -> ValidationResult:
    validator = get_validator_for_path(path)
    if validator is None:
        return ValidationResult(passed=True, validator=None, errors=[])
    return validator(path, content)
