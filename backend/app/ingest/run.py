import argparse
import asyncio
from pathlib import Path

import yaml

from app.config import get_settings
from app.ingest.discovery import discover_documents, parse_keywords
from app.ingest.fetch import PoliteFetcher
from app.ingest.models import GoldDocument
from app.ingest.repository import PostgresRepository
from app.ingest.service import IngestService

LIVE_SOURCES = ("drafts", "notifications", "masterdirs", "withdrawn")
ALL_SOURCES = ("gold", *LIVE_SOURCES)
LISTING_URLS = {
    "drafts": "https://www.rbi.org.in/Scripts/DraftNotificationsGuildelines.aspx",
    "notifications": "https://www.rbi.org.in/Scripts/NotificationUser.aspx",
    "masterdirs": "https://www.rbi.org.in/Scripts/BS_ViewMasterDirections.aspx",
    "withdrawn": "https://www.rbi.org.in/Scripts/NotificationUserWithdrawnCircular.aspx",
}


def _load_gold(path: Path) -> list[GoldDocument]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    documents = raw.get("documents", [])
    return [
        GoldDocument(
            key=item["key"],
            title=item["title"],
            source_url=item["source_url"],
            expected_clauses=tuple(item.get("expected_clauses", [])),
            rbi_ref=item.get("rbi_ref"),
            dept_ref=item.get("dept_ref"),
            published_at=item.get("published_at"),
        )
        for item in documents
    ]


async def run_source(
    source_name: str,
    manifest: Path = Path("data/gold/corpus.yaml"),
    keyword_value: str | None = None,
) -> int:
    if source_name not in ALL_SOURCES:
        raise ValueError(f"unsupported ingest source: {source_name}")

    settings = get_settings()
    fetcher = PoliteFetcher(
        cache_dir=settings.raw_cache_dir,
        user_agent=settings.rbi_user_agent,
        interval_seconds=settings.rbi_request_interval_seconds,
    )
    repository = PostgresRepository(settings.database_url)
    service = IngestService(fetcher=fetcher, repository=repository)
    run_id = await repository.start_run(source_name)
    failures = 0
    outcomes: dict[str, object] = {}

    try:
        if source_name == "gold":
            sources = _load_gold(manifest)
        else:
            listing_url = LISTING_URLS[source_name]
            listing = await fetcher.fetch(listing_url)
            keywords = parse_keywords(keyword_value or settings.rbi_discovery_keywords)
            sources = discover_documents(
                source=source_name,
                listing_url=listing_url,
                content=listing.content,
                keywords=keywords,
                max_matches=settings.rbi_discovery_max_matches_per_source,
            )
            print(
                f"{source_name}: discovered {len(sources)} matching document(s) "
                f"from {listing_url}"
            )
            outcomes["discovery"] = {
                "listing_url": listing_url,
                "keywords": list(keywords),
                "matches": len(sources),
            }

        for source in sources:
            try:
                result = await service.ingest(source)
                action = "created" if result.created else "unchanged"
                outcomes[source.key] = {
                    "status": action,
                    "version": result.version_no,
                    "clauses": result.clause_count,
                    "content_hash": result.content_hash,
                    "source_url": source.source_url,
                }
                print(
                    f"{source.key}: {action}; version={result.version_no}; "
                    f"clauses={result.clause_count}; sha256={result.content_hash}"
                )
            except Exception as error:  # CLI boundary: report every source and continue.
                failures += 1
                outcomes[source.key] = {
                    "status": "failed",
                    "error": str(error),
                    "source_url": source.source_url,
                }
                print(f"{source.key}: failed: {error}")
    except Exception as error:
        failures += 1
        outcomes["discovery"] = {"status": "failed", "error": str(error)}
        print(f"{source_name}: discovery failed: {error}")

    await repository.finish_run(
        run_id,
        succeeded=failures == 0,
        details={"documents": outcomes, "failure_count": failures},
    )
    return 1 if failures else 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest official RBI documents")
    parser.add_argument("--source", required=True, choices=ALL_SOURCES)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("data/gold/corpus.yaml"),
    )
    parser.add_argument(
        "--keywords",
        help="comma-separated title keywords; defaults to RBI_DISCOVERY_KEYWORDS",
    )
    args = parser.parse_args()
    return asyncio.run(run_source(args.source, args.manifest, args.keywords))


if __name__ == "__main__":
    raise SystemExit(main())
