from app.ingest.worker import schedule_specs


def test_live_sources_are_scheduled_at_required_cadence() -> None:
    specs = {spec.source: spec for spec in schedule_specs()}

    assert specs["drafts"].cron == {
        "day_of_week": "mon-fri",
        "hour": "*/3",
        "minute": "0",
    }
    assert specs["notifications"].cron == {
        "day_of_week": "mon-fri",
        "hour": "*/3",
        "minute": "20",
    }
    assert specs["masterdirs"].cron == {"hour": "1", "minute": "0"}
    assert specs["withdrawn"].cron == {"hour": "2", "minute": "0"}
