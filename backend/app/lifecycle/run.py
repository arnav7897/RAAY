import asyncio
from datetime import date

from app.config import get_settings
from app.ingest.repository import PostgresRepository
from app.lifecycle.compute import compute_lifecycle
from app.lifecycle.repository import LifecycleRepository


async def run() -> int:
    settings = get_settings()
    audit = PostgresRepository(settings.database_url)
    run_id = await audit.start_run("lifecycle")
    repository = LifecycleRepository(settings.database_url)
    try:
        documents = await repository.load_documents()
        states: dict[str, int] = {}
        for document in documents:
            result = compute_lifecycle(
                draft=document.draft,
                effective_at=document.effective_at,
                relations=document.relations,
                as_of=date.today(),
            )
            await repository.update_state(document.document_id, result.state)
            states[result.state.value] = states.get(result.state.value, 0) + 1
    except Exception as error:
        await audit.finish_run(run_id, succeeded=False, details={"error": str(error)})
        print(f"lifecycle: failed: {error}")
        return 1
    details: dict[str, object] = {"documents_processed": len(documents), "states": states}
    await audit.finish_run(run_id, succeeded=True, details=details)
    print(f"lifecycle: updated {len(documents)} document(s): {states}")
    return 0


def main() -> int:
    return asyncio.run(run())


if __name__ == "__main__":
    raise SystemExit(main())
