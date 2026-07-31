"""Pytest fixtures for zotero-mcp tests"""

from typing import Any
from unittest.mock import MagicMock

import pytest
from pyzotero import zotero


@pytest.fixture
def mock_zotero(monkeypatch) -> MagicMock:
    """Fixture that returns a mocked Zotero client"""
    mock = MagicMock(spec=zotero.Zotero)

    def mock_get_zotero_client():
        return mock

    monkeypatch.setattr("zotero_mcp.get_zotero_client", mock_get_zotero_client)
    return mock


@pytest.fixture
def sample_item() -> dict[str, Any]:
    """Fixture that returns a sample Zotero item"""
    return {
        "key": "ABCD1234",
        "data": {
            "key": "ABCD1234",
            "itemType": "journalArticle",
            "title": "Test Article",
            "date": "2024",
            "creators": [
                {"firstName": "John", "lastName": "Doe"},
                {"firstName": "Jane", "lastName": "Smith"},
            ],
            "abstractNote": "This is a test abstract",
            "tags": [{"tag": "test"}, {"tag": "article"}],
            "url": "https://example.com",
            "DOI": "10.1234/test",
        },
        "meta": {"numChildren": 2},
    }


@pytest.fixture
def sample_annotation() -> dict[str, Any]:
    """Fixture that returns a sample Zotero annotation item"""
    return {
        "key": "ANNO1234",
        "data": {
            "key": "ANNO1234",
            "itemType": "annotation",
            "parentItem": "XYZ789",
            "annotationType": "highlight",
            "annotationText": "The highlighted passage",
            "annotationComment": "A comment on the passage",
            "annotationColor": "#2ea8e5",
            "annotationPageLabel": "7",
            "dateModified": "2024-01-01T00:00:00Z",
            "tags": [{"tag": "important"}],
        },
    }


@pytest.fixture
def legacy_item() -> dict[str, Any]:
    """Sample item as an older Zotero returns it: no citationKey, no PMID/PMCID,
    and a Better BibTeX citation key pinned into the Extra field."""
    return {
        "key": "OLD12345",
        "data": {
            "key": "OLD12345",
            "itemType": "journalArticle",
            "title": "Legacy Article",
            "date": "2019",
            "publicationTitle": "Journal of Legacy Studies",
            "extra": "Citation Key: doe2019legacy\nPMID: 12345678",
        },
    }


@pytest.fixture
def sample_attachment() -> dict[str, Any]:
    """Fixture that returns a sample Zotero attachment item"""
    return {
        "key": "XYZ789",
        "data": {
            "key": "XYZ789",
            "itemType": "attachment",
            "contentType": "application/pdf",
            "md5": "123456789",
        },
    }
