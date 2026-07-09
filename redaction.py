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
PUBLIC_CONFIG_PREFIXES = ("NEXT_PUBLIC_", "VITE_", "PUBLIC_")
SECRET_KEY_MARKERS = (
    "TOKEN",
    "PASSWORD",
    "SECRET",
    "API_KEY",
    "PRIVATE_KEY",
    "ENCRYPTION_KEY",
    "AUTH_SECRET",
    "DATABASE_URL",
    "DATABASE_DIRECT_URL",
    "DSN",
    "CONNECTION_STRING",
    "WEBHOOK_SECRET",
    "CLIENT_SECRET",
    "ACCESS_KEY",
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
            normalized_key = key.replace("-", "_")
            if normalized_key.lower().endswith("credential_id"):
                continue
            if not is_secret_key(normalized_key):
                continue
            leaks.append(SecretLeak(path=path, line_number=line_number, key=key))
    return leaks


def assert_no_secret_values(files: Mapping[str, str]) -> None:
    leaks = find_secret_leaks(files)
    if not leaks:
        return

    details = ", ".join(f"{leak.path}:{leak.line_number} {leak.key}" for leak in leaks)
    raise ValueError(f"Secret value detected: {details}")


def is_public_config_key(key: str) -> bool:
    normalized = key.upper().replace("-", "_")
    return normalized.startswith(PUBLIC_CONFIG_PREFIXES)


def is_secret_key(key: str) -> bool:
    normalized = key.upper().replace("-", "_")
    if is_public_config_key(normalized):
        return False
    return any(marker in normalized for marker in SECRET_KEY_MARKERS)


def _is_secret_key(key: str) -> bool:
    return is_secret_key(key)
