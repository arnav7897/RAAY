import asyncio
from dataclasses import dataclass

from apscheduler.schedulers.asyncio import AsyncIOScheduler  # type: ignore[import-untyped]
from apscheduler.triggers.cron import CronTrigger  # type: ignore[import-untyped]

from app.config import get_settings
from app.ingest.run import LIVE_SOURCES, run_source


@dataclass(frozen=True, slots=True)
class ScheduleSpec:
    source: str
    cron: dict[str, str]


def schedule_specs() -> tuple[ScheduleSpec, ...]:
    return (
        ScheduleSpec(
            source="drafts",
            cron={"day_of_week": "mon-fri", "hour": "*/3", "minute": "0"},
        ),
        ScheduleSpec(
            source="notifications",
            cron={"day_of_week": "mon-fri", "hour": "*/3", "minute": "20"},
        ),
        ScheduleSpec(source="masterdirs", cron={"hour": "1", "minute": "0"}),
        ScheduleSpec(source="withdrawn", cron={"hour": "2", "minute": "0"}),
    )


async def _serve() -> None:
    settings = get_settings()
    await run_source("gold")
    if settings.rbi_scheduler_run_on_startup:
        for source in LIVE_SOURCES:
            await run_source(source)

    scheduler = AsyncIOScheduler(timezone=settings.rbi_scheduler_timezone)
    for spec in schedule_specs():
        scheduler.add_job(
            run_source,
            CronTrigger(timezone=settings.rbi_scheduler_timezone, **spec.cron),
            args=(spec.source,),
            id=f"rbi-{spec.source}",
            max_instances=1,
            coalesce=True,
            misfire_grace_time=3600,
        )
    scheduler.start()
    try:
        await asyncio.Event().wait()
    finally:
        scheduler.shutdown(wait=True)


def main() -> None:
    asyncio.run(_serve())


if __name__ == "__main__":
    main()
