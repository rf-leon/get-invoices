#!/usr/bin/env python3
"""Idempotently reconcile filing metadata on one Paperless invoice document."""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urljoin
from urllib.request import Request, urlopen


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Resolve one Paperless invoice and reconcile configured filing metadata "
            "while preserving unrelated classifications."
        )
    )
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--document-id", type=int)
    target.add_argument("--invoice-number")
    parser.add_argument(
        "--provider",
        help="Provider text required when resolving by invoice number.",
    )
    parser.add_argument("--ensure-tag", action="append", type=int, default=[])
    parser.add_argument("--remove-tag", action="append", type=int, default=[])
    parser.add_argument("--ensure-correspondent", type=int)
    parser.add_argument("--ensure-document-type", type=int)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--url-env", default="PAPERLESS_URL")
    parser.add_argument("--token-env", default="PAPERLESS_TOKEN")
    args = parser.parse_args()

    if args.invoice_number and not args.provider:
        parser.error("--provider is required with --invoice-number")
    overlap = set(args.ensure_tag) & set(args.remove_tag)
    if overlap:
        parser.error(f"tag IDs cannot be both required and removed: {sorted(overlap)}")
    return args


class PaperlessClient:
    def __init__(self, base_url: str, token: str) -> None:
        self.base_url = base_url.rstrip("/") + "/"
        self.token = token

    def request(
        self, path: str, *, method: str = "GET", payload: dict[str, Any] | None = None
    ) -> Any:
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        request = Request(
            urljoin(self.base_url, path.lstrip("/")),
            data=body,
            method=method,
            headers={
                "Accept": "application/json",
                "Authorization": f"Token {self.token}",
                **({"Content-Type": "application/json"} if body is not None else {}),
            },
        )
        try:
            with urlopen(request, timeout=30) as response:
                return json.load(response)
        except HTTPError as error:
            message = error.read(1000).decode("utf-8", errors="replace")
            raise RuntimeError(f"Paperless HTTP {error.code}: {message}") from error
        except URLError as error:
            raise RuntimeError(f"Paperless connection failed: {error.reason}") from error

    def get_document(self, document_id: int) -> dict[str, Any]:
        return self.request(f"api/documents/{document_id}/")

    def find_invoice(self, provider: str, invoice_number: str) -> dict[str, Any]:
        query = urlencode({"query": invoice_number, "page_size": 100})
        response = self.request(f"api/documents/?{query}")
        provider_lower = provider.casefold()
        matches = []
        for document in response.get("results", []):
            title = str(document.get("title") or "")
            content = str(document.get("content") or "")
            haystack = f"{title}\n{content}"
            if invoice_number in haystack and provider_lower in haystack.casefold():
                matches.append(document)

        if len(matches) != 1:
            ids = [document.get("id") for document in matches]
            raise RuntimeError(
                "Expected exactly one Paperless document for "
                f"{provider} invoice {invoice_number}; found {len(matches)} (ids={ids})"
            )
        return matches[0]

    def patch_document(
        self, document_id: int, payload: dict[str, Any]
    ) -> dict[str, Any]:
        return self.request(
            f"api/documents/{document_id}/",
            method="PATCH",
            payload=payload,
        )


def main() -> int:
    args = parse_args()
    base_url = os.environ.get(args.url_env)
    token = os.environ.get(args.token_env)
    if not base_url or not token:
        raise RuntimeError(
            f"Set {args.url_env} and {args.token_env} before running this helper"
        )

    client = PaperlessClient(base_url, token)
    if args.document_id is not None:
        document = client.get_document(args.document_id)
    else:
        document = client.find_invoice(args.provider, args.invoice_number)

    document_id = int(document["id"])
    current_tags = {int(tag) for tag in document.get("tags", [])}
    desired_tags = sorted((current_tags | set(args.ensure_tag)) - set(args.remove_tag))
    current_correspondent = document.get("correspondent")
    current_document_type = document.get("document_type")
    desired_correspondent = (
        args.ensure_correspondent
        if args.ensure_correspondent is not None
        else current_correspondent
    )
    desired_document_type = (
        args.ensure_document_type
        if args.ensure_document_type is not None
        else current_document_type
    )
    changed = (
        desired_tags != sorted(current_tags)
        or desired_correspondent != current_correspondent
        or desired_document_type != current_document_type
    )

    if changed and not args.dry_run:
        client.patch_document(
            document_id,
            {
                "tags": desired_tags,
                "correspondent": desired_correspondent,
                "document_type": desired_document_type,
            },
        )
        verified = client.get_document(document_id)
        verified_tags = sorted(int(tag) for tag in verified.get("tags", []))
        verified_correspondent = verified.get("correspondent")
        verified_document_type = verified.get("document_type")
        if (
            verified_tags != desired_tags
            or verified_correspondent != desired_correspondent
            or verified_document_type != desired_document_type
        ):
            raise RuntimeError(
                f"Paperless verification failed for document {document_id}: "
                f"expected tags/correspondent/type "
                f"{desired_tags}/{desired_correspondent}/{desired_document_type}, got "
                f"{verified_tags}/{verified_correspondent}/{verified_document_type}"
            )
    else:
        verified_tags = sorted(current_tags) if args.dry_run else desired_tags
        verified_correspondent = current_correspondent
        verified_document_type = current_document_type

    print(
        json.dumps(
            {
                "document_id": document_id,
                "title": document.get("title"),
                "old_tags": sorted(current_tags),
                "desired_tags": desired_tags,
                "verified_tags": verified_tags,
                "old_correspondent": current_correspondent,
                "desired_correspondent": desired_correspondent,
                "verified_correspondent": verified_correspondent,
                "old_document_type": current_document_type,
                "desired_document_type": desired_document_type,
                "verified_document_type": verified_document_type,
                "changed": changed,
                "dry_run": args.dry_run,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(1) from error
