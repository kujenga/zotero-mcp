"""Tests for item metadata and fulltext operations"""

from typing import Any

from zotero_mcp import get_item_metadata, get_item_fulltext


def test_get_item_metadata(mock_zotero: Any, sample_item: dict[str, Any]) -> None:
    """Test retrieving item metadata"""
    mock_zotero.item.return_value = sample_item

    result = get_item_metadata("ABCD1234")

    assert "## Test Article" in result
    assert "Item Key: `ABCD1234`" in result
    assert "Type: journalArticle" in result
    assert "Date: 2024" in result
    assert "Doe, John; Smith, Jane" in result
    assert "### Abstract" in result
    assert "This is a test abstract" in result
    assert "### Tags" in result
    assert "`test`" in result and "`article`" in result
    assert "URL: https://example.com" in result
    assert "DOI: 10.1234/test" in result
    assert "Number of notes/attachments: 2" in result


def test_get_item_metadata_not_found(mock_zotero: Any) -> None:
    """Test retrieving metadata for nonexistent item"""
    mock_zotero.item.return_value = None

    result = get_item_metadata("NONEXISTENT")

    assert "No item found" in result


def test_get_item_fulltext(
    mock_zotero: Any, sample_item: dict[str, Any], sample_attachment: dict[str, Any]
) -> None:
    """Test retrieving item fulltext"""
    mock_zotero.item.return_value = sample_item
    mock_zotero.children.return_value = [sample_attachment]
    mock_zotero.fulltext_item.return_value = {"content": "Sample full text content"}

    result = get_item_fulltext("ABCD1234")

    assert "Test Article" in result
    assert "Sample full text content" in result
    assert "XYZ789" in result  # Attachment key


def test_get_item_fulltext_no_attachment(
    mock_zotero: Any, sample_item: dict[str, Any]
) -> None:
    """Test retrieving fulltext when no attachment is available"""
    mock_zotero.item.return_value = sample_item
    mock_zotero.children.return_value = []

    result = get_item_fulltext("ABCD1234")

    assert "No suitable attachment found" in result
