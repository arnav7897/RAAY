import argparse
import asyncio
from pathlib import Path

import yaml

from app.config import get_settings
from app.ingest.fetch import PoliteFetcher
from app.ingest.models import GoldDocument
from app.ingest.repository import PostgresRepository
from app.ingest.service import IngestService


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


async def _run_gold(manifest: Path) -> int:
    settings = get_settings()
    fetcher = PoliteFetcher(
        cache_dir=settings.raw_cache_dir,
        user_agent=settings.rbi_user_agent,
        interval_seconds=settings.rbi_request_interval_seconds,
    )
    repository = PostgresRepository(settings.database_url)
    service = IngestService(
        fetcher=fetcher,
        repository=repository,
    )
    run_id = await repository.start_run("gold")
    failures = 0
    outcomes: dict[str, object] = {}
    for source in _load_gold(manifest):
        try:
            result = await service.ingest(source)
            action = "created" if result.created else "unchanged"
            outcomes[source.key] = {
                "status": action,
                "version": result.version_no,
                "clauses": result.clause_count,
                "content_hash": result.content_hash,
            }
            print(
                f"{source.key}: {action}; version={result.version_no}; "
                f"clauses={result.clause_count}; sha256={result.content_hash}"
            )
        except Exception as error:  # CLI boundary: report every source and continue.
            failures += 1
            outcomes[source.key] = {"status": "failed", "error": str(error)}
            print(f"{source.key}: failed: {error}")
    await repository.finish_run(
        run_id,
        succeeded=failures == 0,
        details={"documents": outcomes, "failure_count": failures},
    )
    return 1 if failures else 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest official RBI documents")
    parser.add_argument(
        "--source",
        required=True,
        choices=("gold", "drafts", "notifications", "masterdirs", "withdrawn"),
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("data/gold/corpus.yaml"),
    )
    args = parser.parse_args()
    if args.source != "gold":
        parser.error(f"source {args.source!r} is planned but not implemented in Phase 1")
    return asyncio.run(_run_gold(args.manifest))


if __name__ == "__main__":
    raise SystemExit(main())
