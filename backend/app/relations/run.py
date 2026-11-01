import asyncio

from app.config import get_settings
from app.ingest.repository import PostgresRepository
from app.relations.reconcile import RelationshipReconciler
from app.relations.repository import RelationshipRepository


async def run() -> int:
    settings = get_settings()
    audit_repository = PostgresRepository(settings.database_url)
    run_id = await audit_repository.start_run("relationships")
    try:
        reconciler = RelationshipReconciler(
            repository=RelationshipRepository(settings.database_url),
            raw_cache_dir=settings.raw_cache_dir,
        )
        summary = await reconciler.reconcile()
    except Exception as error:
        await audit_repository.finish_run(
            run_id,
            succeeded=False,
            details={"error": str(error)},
        )
        print(f"relationships: failed: {error}")
        return 1

    details: dict[str, object] = {
        "sources_processed": summary.sources_processed,
        "sources_skipped": summary.sources_skipped,
        "relationships_seen": summary.relationships_seen,
        "failures": list(summary.failures),
    }
    await audit_repository.finish_run(run_id, succeeded=True, details=details)
    print(
        f"relationships: reconciled {summary.relationships_seen} relationship(s) "
        f"from {summary.sources_processed} source document(s); "
        f"skipped {summary.sources_skipped}"
    )
    return 0


def main() -> int:
    return asyncio.run(run())


if __name__ == "__main__":
    raise SystemExit(main())
