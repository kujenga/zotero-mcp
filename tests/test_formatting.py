"""Tests for item metadata formatting, including cross-version compatibility"""

from typing import Any

import pytest

from zotero_mcp import format_item, get_citation_key, get_source


def test_citation_key_native_field(sample_item: dict[str, Any]) -> None:
    """Zotero 8+ exposes citationKey as a native field"""
    sample_item["data"]["citationKey"] = "doe2024test"

    assert get_citation_key(sample_item["data"]) == "doe2024test"
    assert "Citation Key: `doe2024test`" in format_item(sample_item)


def test_citation_key_from_extra(legacy_item: dict[str, Any]) -> None:
    """Older Zotero versions only have Better BibTeX's pinned key in Extra"""
    assert get_citation_key(legacy_item["data"]) == "doe2019legacy"
    assert "Citation Key: `doe2019legacy`" in format_item(legacy_item)


def test_citation_key_native_field_wins(legacy_item: dict[str, Any]) -> None:
    """Zotero 8 migrated pinned keys, so the native field takes precedence"""
    legacy_item["data"]["citationKey"] = "migrated2019key"

    assert get_citation_key(legacy_item["data"]) == "migrated2019key"


def test_citation_key_absent(sample_item: dict[str, Any]) -> None:
    """Items without a citation key render no Citation Key line"""
    assert get_citation_key(sample_item["data"]) is None
    assert "Citation Key" not in format_item(sample_item)


@pytest.mark.parametrize(
    ("item_type", "fields", "expected"),
    [
        ("journalArticle", {"publicationTitle": "Nature"}, "Nature"),
        ("preprint", {"repository": "arXiv"}, "arXiv"),
        ("conferencePaper", {"proceedingsTitle": "WACV 2023"}, "WACV 2023"),
        ("bookSection", {"bookTitle": "A Book", "publisher": "Pub"}, "In: A Book"),
        ("book", {"publisher": "Pub"}, "Pub"),
        ("blogPost", {"blogTitle": "A Blog"}, "A Blog"),
        ("webpage", {"websiteTitle": "A Site"}, "A Site"),
        ("report", {"institution": "An Institute"}, "An Institute"),
        ("thesis", {"university": "A University"}, "A University"),
        ("manuscript", {}, None),
    ],
)
def test_get_source_by_item_type(
    item_type: str, fields: dict[str, str], expected: str | None
) -> None:
    """Every item type reports its own source of record, not just journals"""
    assert get_source({"itemType": item_type, **fields}) == expected


def test_source_rendered_for_non_journal_items(sample_item: dict[str, Any]) -> None:
    """A preprint surfaces its repository in the full metadata view"""
    sample_item["data"]["itemType"] = "preprint"
    sample_item["data"]["repository"] = "arXiv"
    sample_item["data"]["archiveID"] = "arXiv:2401.00001"

    result = format_item(sample_item)

    assert "Repository: arXiv" in result
    assert "Archive ID: arXiv:2401.00001" in result


def test_timestamps_included(sample_item: dict[str, Any]) -> None:
    """The single-item view reports provenance timestamps"""
    sample_item["data"]["dateAdded"] = "2024-01-01T00:00:00Z"
    sample_item["data"]["dateModified"] = "2024-02-02T00:00:00Z"
    sample_item["data"]["accessDate"] = "2024-03-03T00:00:00Z"

    result = format_item(sample_item)

    assert "### Timestamps" in result
    assert "Date Added: 2024-01-01T00:00:00Z" in result
    assert "Date Modified: 2024-02-02T00:00:00Z" in result
    assert "Accessed: 2024-03-03T00:00:00Z" in result


def test_extra_and_identifiers(sample_item: dict[str, Any]) -> None:
    """Extra is surfaced verbatim and newer identifiers are grouped"""
    sample_item["data"]["extra"] = "arXiv:2401.00001 [cs.LG]"
    sample_item["data"]["PMID"] = "12345678"
    sample_item["data"]["PMCID"] = "PMC1234567"

    result = format_item(sample_item)

    assert "### Extra\narXiv:2401.00001 [cs.LG]" in result
    assert "PMID: 12345678" in result
    assert "PMCID: PMC1234567" in result


def test_unknown_future_field_still_rendered(sample_item: dict[str, Any]) -> None:
    """Fields from newer schema versions surface without a code change"""
    sample_item["data"]["someFutureField"] = "future value"

    result = format_item(sample_item)

    assert "### Other Fields" in result
    assert "Some Future Field: future value" in result


def test_legacy_item_renders_without_newer_fields(legacy_item: dict[str, Any]) -> None:
    """An older Zotero payload renders cleanly, omitting sections it can't fill"""
    result = format_item(legacy_item)

    assert "## Legacy Article" in result
    assert "Publication: Journal of Legacy Studies" in result
    # No populated fields for these sections, so they are omitted entirely.
    assert "### Timestamps" not in result
    assert "### File" not in result
    assert "### Other Fields" not in result


def test_minimal_item_does_not_raise() -> None:
    """A payload with almost nothing in it still formats"""
    result = format_item({"key": "MIN00001", "data": {"itemType": "document"}})

    assert "Item Key: `MIN00001`" in result
    assert "Untitled" in result


def test_format_annotation(sample_annotation: dict[str, Any]) -> None:
    """Annotations render their highlighted text rather than an empty stub"""
    result = format_item(sample_annotation)

    assert "Highlight Annotation" in result
    assert "Item Key: `ANNO1234`" in result
    assert "Parent Item: `XYZ789`" in result
    assert "Page: 7" in result
    assert "### Highlighted Text\nThe highlighted passage" in result
    assert "### Comment\nA comment on the passage" in result
    assert "`important`" in result


def test_format_note_unchanged(sample_item: dict[str, Any]) -> None:
    """Notes keep their dedicated rendering"""
    note = {
        "key": "NOTE1234",
        "data": {
            "itemType": "note",
            "note": "<p>A <strong>note</strong> body</p>",
            "parentItem": "ABCD1234",
        },
    }

    result = format_item(note)

    assert "## 📝 Note" in result
    assert "Parent Item: `ABCD1234`" in result
    assert "A **note** body" in result
