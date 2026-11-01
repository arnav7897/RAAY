import pytest

from app.ingest.discovery import discover_documents, parse_keywords

LISTING_HTML = b"""
<html><body><table>
  <tr><td class="tableheader"><b>Oct 23, 2026</b></td></tr>
  <tr><td><a class="link2" href=NotificationUser.aspx?Id=13744&Mode=0>
    Reserve Bank of India (NBFC - Credit Facilities) Amendment Directions, 2026
  </a></td></tr>
  <tr><td><a href="https://example.com/NotificationUser.aspx?Id=999">
    NBFC document on an untrusted host
  </a></td></tr>
  <tr><td><a href="/Scripts/NotificationUser.aspx?Id=13745&Mode=0">
    Delegation of Compounding under FEMA
  </a></td></tr>
  <tr><td><a href="/Scripts/NotificationUser.aspx?Id=13744&Mode=0">
    Duplicate NBFC link
  </a></td></tr>
</table></body></html>
"""


def test_discovery_filters_titles_by_keyword_and_deduplicates_urls() -> None:
    documents = discover_documents(
        source="notifications",
        listing_url="https://www.rbi.org.in/Scripts/NotificationUser.aspx",
        content=LISTING_HTML,
        keywords=("nbfc", "microfinance"),
        max_matches=10,
    )

    assert len(documents) == 1
    document = documents[0]
    assert document.title == (
        "Reserve Bank of India (NBFC - Credit Facilities) Amendment Directions, 2026"
    )
    assert document.source_url == (
        "https://www.rbi.org.in/Scripts/NotificationUser.aspx?Id=13744"
    )
    assert document.published_at == "2026-10-23"
    assert document.key.startswith("discovered-notifications-")


def test_discovery_supports_master_direction_and_press_release_links() -> None:
    content = b"""
    <table>
      <tr><td>Sep 11, 2026</td><td>
        <a href="BS_PressReleaseDisplay.aspx?prid=63587">Draft KYC Directions</a>
      </td></tr>
      <tr><td>Nov 28, 2025</td><td>
        <a href=" https://rbi.org.in/Scripts/BS_ViewMasDirections.aspx?id=12933&Mode=0 ">
          Master Direction for Microfinance Institutions
        </a>
      </td></tr>
    </table>
    """

    draft = discover_documents(
        source="drafts",
        listing_url="https://www.rbi.org.in/Scripts/DraftNotificationsGuildelines.aspx",
        content=content,
        keywords=("kyc",),
        max_matches=10,
    )
    master = discover_documents(
        source="masterdirs",
        listing_url="https://www.rbi.org.in/Scripts/BS_ViewMasterDirections.aspx",
        content=content,
        keywords=("microfinance",),
        max_matches=10,
    )

    assert draft[0].source_url.endswith("BS_PressReleaseDisplay.aspx?prid=63587")
    assert draft[0].published_at == "2026-09-11"
    assert master[0].source_url.endswith("BS_ViewMasDirections.aspx?Id=12933")
    assert master[0].published_at == "2025-11-28"


def test_discovery_limits_matches_to_avoid_broad_archive_crawl() -> None:
    content = b"""
    <table><tr><td>
      <a href="NotificationUser.aspx?Id=1">NBFC first</a>
      <a href="NotificationUser.aspx?Id=2">NBFC second</a>
    </td></tr></table>
    """

    documents = discover_documents(
        source="notifications",
        listing_url="https://www.rbi.org.in/Scripts/NotificationUser.aspx",
        content=content,
        keywords=("nbfc",),
        max_matches=1,
    )

    assert [document.title for document in documents] == ["NBFC first"]


def test_empty_keyword_configuration_is_rejected() -> None:
    with pytest.raises(ValueError, match="at least one discovery keyword"):
        parse_keywords(" , ")


def test_keywords_are_trimmed_casefolded_and_deduplicated() -> None:
    assert parse_keywords(" NBFC, microfinance,nbfc, Know Your Customer ") == (
        "nbfc",
        "microfinance",
        "know your customer",
    )
