from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Mapping


SECRET_ASSIGNMENT_RE = re.compile(
    r"(?P<key>[A-Za-z_][A-Za-z0-9_-]*)"
    r"\s*[:=]\s*"
    r"(?P<value>['\"]?[A-Za-z0-9][A-Za-z0-9._~:/+=@-]{8,}['\"]?)",
    re.IGNORECASE,
)
SECRET_VALUE_RE = re.compile(
    r"(github_pat_[A-Za-z0-9_]{20,}|gh[pousr]_[A-Za-z0-9_]{20,}|glpat-[A-Za-z0-9_-]{20,})"
)


@dataclass(frozen=True)
class SecretLeak:
    path: str
    line_number: int
    key: str


def find_secret_leaks(files: Mapping[str, str]) -> list[SecretLeak]:
    leaks: list[SecretLeak] = []
    for path, content in files.items():
        for line_number, line in enumerate(content.splitlines(), start=1):
            if SECRET_VALUE_RE.search(line):
                leaks.append(SecretLeak(path=path, line_number=line_number, key="secret_value"))
                continue
            match = SECRET_ASSIGNMENT_RE.search(line)
            if not match:
                continue
            key = match.group("key")
            normalized_key = key.lower().replace("-", "_")
            if normalized_key.endswith("credential_id"):
                continue
            if not _is_secret_key(normalized_key):
                continue
            leaks.append(SecretLeak(path=path, line_number=line_number, key=key))
    return leaks


def assert_no_secret_values(files: Mapping[str, str]) -> None:
    leaks = find_secret_leaks(files)
    if not leaks:
        return

    details = ", ".join(f"{leak.path}:{leak.line_number} {leak.key}" for leak in leaks)
    raise ValueError(f"Secret value detected: {details}")


def _is_secret_key(key: str) -> bool:
    return any(marker in key for marker in ("token", "password", "secret", "api_key"))
