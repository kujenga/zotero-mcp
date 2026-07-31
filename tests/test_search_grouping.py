"""Tests for resolving child-item search hits back to the work they belong to"""

from typing import Any

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
    assert "**Matched in**: attachment full text `ATT00001`" in result


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

    assert [item["key"] for item, _ in grouped] == ["PARENT02", "PARENT01"]


def test_resolution_survives_a_failed_lookup(mock_zotero: Any) -> None:
    """An API error while resolving degrades to rendering the child item"""
    mock_zotero.items.side_effect = [
        [child("ATT00001", "PARENT01", title="Some PDF")],
        RuntimeError("api exploded"),
    ]

    result = search_items("test", qmode="everything")

    assert "Some PDF" in result


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
