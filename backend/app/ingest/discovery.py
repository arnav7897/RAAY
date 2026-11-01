import hashlib
import re
from datetime import datetime
from urllib.parse import parse_qsl, urljoin, urlparse

from selectolax.parser import HTMLParser

from app.ingest.models import GoldDocument
from app.parse.text import normalize_text

_ALLOWED_ENDPOINTS = {
    "drafts": {
        "/scripts/bs_pressreleasedisplay.aspx": "prid",
        "/scripts/notificationuser.aspx": "id",
    },
    "notifications": {"/scripts/notificationuser.aspx": "id"},
    "masterdirs": {"/scripts/bs_viewmasdirections.aspx": "id"},
    "withdrawn": {"/scripts/notificationuser.aspx": "id"},
}
_CANONICAL_PATHS = {
    "/scripts/bs_pressreleasedisplay.aspx": "/Scripts/BS_PressReleaseDisplay.aspx",
    "/scripts/notificationuser.aspx": "/Scripts/NotificationUser.aspx",
    "/scripts/bs_viewmasdirections.aspx": "/Scripts/BS_ViewMasDirections.aspx",
}
_DATE_PATTERN = re.compile(
    r"\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|June?|July?|"
    r"Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
    r"\s+\d{1,2},\s+\d{4}\b",
    re.IGNORECASE,
)


def parse_keywords(value: str) -> tuple[str, ...]:
    keywords = tuple(
        dict.fromkeys(part.strip().casefold() for part in value.split(",") if part.strip())
    )
    if not keywords:
        raise ValueError("at least one discovery keyword is required")
    return keywords


def _published_date(text: str) -> str | None:
    match = _DATE_PATTERN.search(text)
    if match is None:
        return None
    value = match.group(0)
    for pattern in ("%b %d, %Y", "%B %d, %Y"):
        try:
            return datetime.strptime(value, pattern).date().isoformat()
        except ValueError:
            continue
    return None


def _canonical_document_url(source: str, listing_url: str, href: str) -> str | None:
    absolute = urljoin(listing_url, href.strip())
    parsed = urlparse(absolute)
    if parsed.scheme.casefold() not in {"http", "https"}:
        return None
    if parsed.hostname is None or parsed.hostname.casefold() not in {
        "rbi.org.in",
        "www.rbi.org.in",
    }:
        return None
    path = parsed.path.casefold()
    parameter = _ALLOWED_ENDPOINTS.get(source, {}).get(path)
    if parameter is None:
        return None
    query = {key.casefold(): value for key, value in parse_qsl(parsed.query)}
    identifier = query.get(parameter)
    if identifier is None or not identifier.isdigit():
        return None
    display_parameter = "prid" if parameter == "prid" else "Id"
    return (
        f"https://www.rbi.org.in{_CANONICAL_PATHS[path]}"
        f"?{display_parameter}={identifier}"
    )


def _source_key(source: str, url: str) -> str:
    digest = hashlib.sha256(url.casefold().encode("utf-8")).hexdigest()[:16]
    return f"discovered-{source}-{digest}"


def discover_documents(
    *,
    source: str,
    listing_url: str,
    content: bytes,
    keywords: tuple[str, ...],
    max_matches: int,
) -> list[GoldDocument]:
    if not keywords:
        raise ValueError("at least one discovery keyword is required")
    if max_matches < 1:
        raise ValueError("max_matches must be positive")
    if source not in _ALLOWED_ENDPOINTS:
        raise ValueError(f"unsupported discovery source: {source}")

    tree = HTMLParser(content)
    documents: list[GoldDocument] = []
    seen_urls: set[str] = set()
    current_date: str | None = None

    for row in tree.css("tr"):
        row_text = normalize_text(row.text(separator=" ", strip=True))
        current_date = _published_date(row_text) or current_date
        for anchor in row.css("a"):
            title = normalize_text(anchor.text(separator=" ", strip=True))
            if not title or not any(keyword in title.casefold() for keyword in keywords):
                continue
            href = anchor.attributes.get("href")
            if href is None:
                continue
            url = _canonical_document_url(source, listing_url, href)
            if url is None or url in seen_urls:
                continue
            seen_urls.add(url)
            documents.append(
                GoldDocument(
                    key=_source_key(source, url),
                    title=title,
                    source_url=url,
                    published_at=current_date,
                )
            )
            if len(documents) == max_matches:
                return documents
    return documents
