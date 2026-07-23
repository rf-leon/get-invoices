#!/usr/bin/env python3
"""Lint bundled provider recipes: allowlisted frontmatter only, no personal data.

Bundled recipes describe websites, not accounts. Anything account-specific
belongs in the user's ~/.config/get-invoices/providers/ overrides.
Exit code 1 with findings on stdout if any recipe violates the rules.
"""

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

ALLOWED_KEYS = {
    "name",
    "description",
    "domain",
    "url",
    "download_pattern",
    "extraction_bridge",
    "billing_email_supported",
    "billing_email_url",
}

PATTERNS = [
    ("email address", re.compile(r"\b[\w.+-]+@[\w-]+\.\w{2,}\b")),
    ("IBAN", re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{11,30}\b")),
    ("long digit run (customer/contract/invoice number?)", re.compile(r"\b\d{7,}\b")),
    ("personal-state field", re.compile(r"^(billing_email_set|company_tag)\s*:", re.M)),
]


def frontmatter_keys(text: str) -> list[str]:
    match = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not match:
        return []
    keys = []
    for line in match.group(1).splitlines():
        m = re.match(r"^([A-Za-z_][\w-]*)\s*:", line)
        if m:
            keys.append(m.group(1))
    return keys


def lint(directory: Path) -> list[str]:
    findings = []
    for path in sorted(directory.glob("*.md")):
        if path.name == "_template.md":
            continue
        text = path.read_text(encoding="utf-8")
        rel = path.relative_to(REPO_ROOT)

        keys = frontmatter_keys(text)
        if not keys:
            findings.append(f"{rel}: missing or unparseable frontmatter")
        for key in keys:
            if key not in ALLOWED_KEYS:
                findings.append(f"{rel}: frontmatter key '{key}' is not allowlisted")

        for label, pattern in PATTERNS:
            for m in pattern.finditer(text):
                line = text.count("\n", 0, m.start()) + 1
                findings.append(f"{rel}:{line}: {label}: {m.group(0)!r}")
    return findings


def main() -> int:
    # Lint the packaged mirror: it is exactly what ships publicly, and the
    # sync --check CI step guarantees it matches the (non-excluded) sources.
    findings = lint(REPO_ROOT / "skills/get-invoices/providers")
    if findings:
        print("Provider lint FAILED:")
        for finding in findings:
            print(f"  {finding}")
        return 1
    print("Provider lint passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
