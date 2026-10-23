from __future__ import annotations

import re
from html.parser import HTMLParser
from urllib.parse import urlparse

_ALLOWED_SCHEMES = {"https"}


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)

    def handle_entityref(self, name: str) -> None:
        self.parts.append(f"&{name};")


def html_to_text(value: str | None) -> str | None:
    if not value:
        return None
    parser = _TextExtractor()
    try:
        parser.feed(value)
        parser.close()
    except Exception:
        stripped = re.sub(r"<[^>]+>", " ", value)
        return _clean_whitespace(stripped)
    return _clean_whitespace(" ".join(parser.parts))


def _clean_whitespace(value: str) -> str:
    text = re.sub(r"\s+", " ", value).strip()
    return text or ""


def sanitize_url(value: str | None, allowed_hosts: tuple[str, ...]) -> str | None:
    if not value:
        return None
    candidate = value.strip()
    if candidate.startswith("//"):
        candidate = "https:" + candidate
    parsed = urlparse(candidate)
    if parsed.scheme.lower() not in _ALLOWED_SCHEMES:
        return None
    host = (parsed.hostname or "").lower()
    if not host:
        return None
    if host not in {h.lower() for h in allowed_hosts}:
        return None
    return parsed.geturl()
