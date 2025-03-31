"""Tests for search functionality"""

from typing import Any

from zotero_mcp import search_items


def test_search_items_basic(mock_zotero: Any, sample_item: dict[str, Any]) -> None:
    """Test basic search functionality"""
    mock_zotero.items.return_value = [sample_item]

    result = search_items("test")

    assert "Test Article" in result
    assert "**Key**: `ABCD1234`" in result
    assert "**Authors**: Doe, John; Smith, Jane" in result
    assert "This is a test abstract" in result

    # Verify search parameters
    mock_zotero.add_parameters.assert_called_once_with(
        q="test", qmode="titleCreatorYear", limit=10
    )


def test_search_items_no_results(mock_zotero: Any) -> None:
    """Test search with no results"""
    mock_zotero.items.return_value = []

    result = search_items("nonexistent")

    assert "No items found" in result


def test_search_items_custom_params(
    mock_zotero: Any, sample_item: dict[str, Any]
) -> None:
    """Test search with custom parameters"""
    mock_zotero.items.return_value = [sample_item]

    search_items("test", qmode="everything", limit=5)

    mock_zotero.add_parameters.assert_called_once_with(
        q="test", qmode="everything", limit=5
    )
