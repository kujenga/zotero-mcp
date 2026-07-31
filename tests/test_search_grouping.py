"""Tests for resolving child-item search hits back to the work they belong to"""

from typing import Any
from unittest.mock import MagicMock

from zotero_mcp import group_by_work, search_items


def child(key: str, parent: str, item_type: str = "attachment", **data: Any) -> dict:
    return {
        "key": key,
        "data": {"key": key, "itemType": item_type, "parentItem": parent, **data},
    }


def work(key: str, title: str = "A Paper") -> dict:
    return {
        "key": key,
        "data": {"key": key, "itemType": "journalArticle", "title": title},
    }


def test_child_hit_resolves_to_its_work(mock_zotero: Any) -> None:
    """A PDF full-text hit is reported as the work, not as an anonymous attachment"""
    parent = work("PARENT01", "Underwater Cyborg Insects")
    mock_zotero.items.side_effect = [[child("ATT00001", "PARENT01")], [parent]]

    result = search_items("oxygen-deprived", qmode="everything")

    assert "Underwater Cyborg Insects" in result
    assert "**Key**: `PARENT01`" in result
    assert "**Matched in**: attachment full text `ATT00001`" in result


def test_work_and_its_child_are_not_duplicated(mock_zotero: Any) -> None:
    """A work matching directly and through its attachment appears once"""
    parent = work("PARENT01")
    mock_zotero.items.return_value = [parent, child("ATT00001", "PARENT01")]

    result = search_items("test", qmode="everything")

    assert result.count("**Key**: `PARENT01`") == 1
    assert "Found 1 items across 2 matches" in result
    # The work matched on its own fields too, so the provenance says so rather
    # than crediting the attachment alone.
    assert "**Matched in**: this item, attachment full text `ATT00001`" in result


def test_direct_and_child_matches_are_distinguishable(mock_zotero: Any) -> None:
    """A work found only via its PDF must not look like one that also matched"""
    mock_zotero.items.side_effect = [
        [
            child("ATT_A", "WORK_A"),
            work("WORK_B", "Matched Both Ways"),
            child("ATT_B", "WORK_B"),
        ],
        [work("WORK_A", "Only Its PDF Matched")],
    ]

    result = search_items("test", qmode="everything")

    assert "**Matched in**: attachment full text `ATT_A`" in result
    assert "**Matched in**: this item, attachment full text `ATT_B`" in result


def test_multiple_children_listed_together(mock_zotero: Any) -> None:
    """Every child match for a work is reported on one line"""
    parent = work("PARENT01")
    mock_zotero.items.side_effect = [
        [
            child("ATT00001", "PARENT01", title="Preprint PDF"),
            child("NOTE0001", "PARENT01", item_type="note", note="<p>a note</p>"),
        ],
        [parent],
    ]

    result = search_items("test", qmode="everything")

    assert "attachment full text (Preprint PDF) `ATT00001`" in result
    assert "note `NOTE0001`" in result


def test_annotation_resolves_two_levels(mock_zotero: Any) -> None:
    """Annotations hang off an attachment, so resolution takes two hops"""
    annotation = child(
        "ANNO0001", "ATT00001", item_type="annotation", annotationType="highlight"
    )
    attachment = child("ATT00001", "PARENT01")
    parent = work("PARENT01", "Coreference Models")
    mock_zotero.items.side_effect = [[annotation], [attachment], [parent]]

    result = search_items("pairwise model", qmode="everything")

    assert "Coreference Models" in result
    assert "**Matched in**: highlight annotation `ANNO0001`" in result


def test_unresolvable_parent_keeps_the_child(mock_zotero: Any) -> None:
    """Nothing that matched is dropped when a parent cannot be fetched"""
    orphan = child("ATT00001", "MISSING1", title="Orphan PDF")
    mock_zotero.items.side_effect = [[orphan], []]

    result = search_items("test", qmode="everything")

    assert "Orphan PDF" in result
    assert "**Key**: `ATT00001`" in result


def test_no_extra_request_without_child_hits(
    mock_zotero: Any, sample_item: dict[str, Any]
) -> None:
    """Searches that match no child items make a single API call"""
    mock_zotero.items.return_value = [sample_item]

    search_items("test")

    assert mock_zotero.items.call_count == 1
    mock_zotero.add_parameters.assert_called_once()


def test_parent_already_in_results_is_not_refetched(mock_zotero: Any) -> None:
    """A parent present in the results does not trigger a lookup"""
    mock_zotero.items.return_value = [work("PARENT01"), child("ATT00001", "PARENT01")]

    search_items("test", qmode="everything")

    assert mock_zotero.items.call_count == 1


def test_group_by_work_preserves_first_match_order() -> None:
    """Grouping keeps the order Zotero returned results in"""
    items = [
        child("ATT00002", "PARENT02"),
        work("PARENT01"),
        child("ATT00001", "PARENT01"),
    ]
    resolved = {"PARENT02": work("PARENT02")}

    grouped = group_by_work(items, resolved)

    assert [group.item["key"] for group in grouped] == ["PARENT02", "PARENT01"]


def test_resolution_survives_a_failed_lookup(mock_zotero: Any) -> None:
    """An API error while resolving degrades to rendering the child item"""
    mock_zotero.items.side_effect = [
        [child("ATT00001", "PARENT01", title="Some PDF")],
        RuntimeError("api exploded"),
    ]

    result = search_items("test", qmode="everything")

    assert "Some PDF" in result


def test_header_reports_resolution_without_any_collapsing(mock_zotero: Any) -> None:
    """Every result resolved through a PDF, but no two share a parent"""
    mock_zotero.items.side_effect = [
        [child(f"ATT0000{i}", f"PARENT0{i}") for i in range(1, 4)],
        [work(f"PARENT0{i}") for i in range(1, 4)],
    ]

    result = search_items("memory persistence", qmode="everything")

    # Nothing collapsed -- works equals matches -- yet the resolution is still
    # reported, which is the whole point. The match count stays as the
    # denominator for "all of which".
    assert (
        "Found 3 items across 3 matches, all of which were inside attachments or notes."
        in result
    )


def test_header_stays_quiet_for_metadata_only_matches(mock_zotero: Any) -> None:
    """Title and creator matches read the same as they always did"""
    mock_zotero.items.return_value = [work("PARENT01"), work("PARENT02")]

    result = search_items("test")

    assert "Found 2 items." in result
    assert "attachments or notes" not in result


def test_header_counts_partial_resolution(mock_zotero: Any) -> None:
    """A mix of metadata and child matches reports how many came from children"""
    mock_zotero.items.side_effect = [
        [work("PARENT01"), work("PARENT02"), child("ATT00001", "PARENT03")],
        [work("PARENT03")],
    ]

    result = search_items("test", qmode="everything")

    assert (
        "Found 3 items across 3 matches, 1 of which were inside attachments or notes."
        in result
    )


def test_header_reports_collapsing_and_resolution_together(mock_zotero: Any) -> None:
    """Both facts appear when both apply"""
    mock_zotero.items.side_effect = [
        [
            child("ATT00001", "PARENT01"),
            child("ATT00002", "PARENT01"),
            work("PARENT02"),
        ],
        [work("PARENT01")],
    ]

    result = search_items("test", qmode="everything")

    assert (
        "Found 2 items across 3 matches, 2 of which were inside attachments or notes."
        in result
    )


def test_hyphenated_query_is_flagged(mock_zotero: Any) -> None:
    """Zotero ORs the halves of a hyphenated term, which nothing else signals"""
    mock_zotero.items.return_value = [work("PARENT01")]

    result = search_items("oxygen-deprived")

    assert "read as OR" in result
    assert "Replace it with a space" in result


def test_unhyphenated_query_is_not_flagged(mock_zotero: Any) -> None:
    """The note only appears when a hyphen actually joins two words"""
    mock_zotero.items.return_value = [work("PARENT01")]

    assert "read as OR" not in search_items("oxygen deprived")
    assert "read as OR" not in search_items("-deprived")


def test_empty_results_suggest_everything_mode(mock_zotero: Any) -> None:
    """The default mode not searching abstracts is worth saying at zero results"""
    mock_zotero.items.return_value = []

    result = search_items("oxygen-deprived")

    assert "qmode='everything'" in result
    assert "titles, creators, and years only" in result


def test_empty_results_in_everything_mode_suggest_nothing(mock_zotero: Any) -> None:
    """There is no wider mode to recommend once everything has been tried"""
    mock_zotero.items.return_value = []

    result = search_items("oxygen-deprived", qmode="everything")

    assert result == "No items found matching your query."


def with_total(mock_zotero: Any, total: int) -> None:
    """Give the mocked client a Total-Results header, as Zotero returns"""
    mock_zotero.request = MagicMock()
    mock_zotero.request.headers = {"Total-Results": str(total)}


def test_truncated_results_report_the_total(mock_zotero: Any) -> None:
    """A capped result set says so, since that is when the caller should re-query"""
    mock_zotero.items.return_value = [work("PARENT01"), work("PARENT02")]
    with_total(mock_zotero, 137)

    result = search_items("test", limit=2)

    assert "first 2 of 137 matches" in result
    assert "raise `limit`" in result


def test_complete_results_say_nothing_extra(mock_zotero: Any) -> None:
    """A complete result set is not qualified, so silence means exhausted"""
    mock_zotero.items.return_value = [work("PARENT01"), work("PARENT02")]
    with_total(mock_zotero, 2)

    result = search_items("test", limit=10)

    assert "of 2 matches" not in result
    assert "Found 2 items." in result


def test_grouped_and_truncated_reports_both(mock_zotero: Any) -> None:
    """Grouping and truncation are distinct facts and both get reported"""
    mock_zotero.items.side_effect = [
        [
            child("ATT00001", "PARENT01"),
            child("ATT00002", "PARENT01"),
            child("ATT00003", "PARENT02"),
        ],
        [work("PARENT01"), work("PARENT02")],
    ]
    with_total(mock_zotero, 99)

    result = search_items("test", qmode="everything", limit=3)

    assert "Found 2 items across 3 matches" in result
    assert "first 3 of 99 matches" in result


def test_fewer_items_than_limit_can_still_be_truncated(mock_zotero: Any) -> None:
    """The case the item count alone cannot express: 4 items from a full page"""
    mock_zotero.items.side_effect = [
        [child(f"ATT0000{i}", "PARENT01") for i in range(1, 11)],
        [work("PARENT01")],
    ]
    with_total(mock_zotero, 1093)

    result = search_items("test", qmode="everything", limit=10)

    assert "Found 1 items across 10 matches" in result
    assert "first 10 of 1093 matches" in result


def test_falls_back_to_limit_when_header_missing(mock_zotero: Any) -> None:
    """Without Total-Results, a full page is still flagged as possibly truncated"""
    mock_zotero.items.return_value = [work("PARENT01"), work("PARENT02")]

    result = search_items("test", limit=2)

    assert "reached the limit of 2 matches" in result


def test_no_truncation_note_when_under_limit_without_header(mock_zotero: Any) -> None:
    """A short page without the header is treated as complete"""
    mock_zotero.items.return_value = [work("PARENT01")]

    result = search_items("test", limit=10)

    assert "reached the limit" not in result
    assert "of 2 matches" not in result


def test_standalone_note_is_unaffected(mock_zotero: Any) -> None:
    """Notes without a parent keep their own rendering"""
    note = {
        "key": "NOTE0001",
        "data": {"key": "NOTE0001", "itemType": "note", "note": "<p>Standalone</p>"},
    }
    mock_zotero.items.return_value = [note]

    result = search_items("test")

    assert "📝" in result
    assert "Standalone" in result
