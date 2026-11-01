import asyncio

from app.applicability.reconcile import ApplicabilityReconciler
from app.applicability.repository import ApplicabilityRepository
from app.config import get_settings
from app.ingest.repository import PostgresRepository


async def run() -> int:
    settings = get_settings()
    audit = PostgresRepository(settings.database_url)
    run_id = await audit.start_run("applicability")
    try:
        summary = await ApplicabilityReconciler(
            repository=ApplicabilityRepository(settings.database_url),
            raw_cache_dir=settings.raw_cache_dir,
        ).reconcile()
    except Exception as error:
        await audit.finish_run(run_id, succeeded=False, details={"error": str(error)})
        print(f"applicability: failed: {error}")
        return 1
    details: dict[str, object] = {
        "sources_processed": summary.sources_processed,
        "sources_skipped": summary.sources_skipped,
        "facts_seen": summary.facts_seen,
    }
    await audit.finish_run(run_id, succeeded=True, details=details)
    print(
        f"applicability: reconciled {summary.facts_seen} fact(s) from "
        f"{summary.sources_processed} source document(s); skipped {summary.sources_skipped}"
    )
    return 0


def main() -> int:
    return asyncio.run(run())


if __name__ == "__main__":
    raise SystemExit(main())
