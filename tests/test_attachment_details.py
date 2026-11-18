"""Tests for deterministic attachment selection and lookup error handling."""

from typing import Any

from zotero_mcp import get_item_fulltext
from zotero_mcp.client import (
    AttachmentDetails,
    get_attachment_details,
    lookup_attachment_details,
)


def _child_attachment(
    key: str,
    content_type: str | None = "application/pdf",
    *,
    md5: str = "",
    link_mode: str | None = None,
    date_added: str | None = None,
) -> dict[str, Any]:
    data: dict[str, Any] = {
        "key": key,
        "itemType": "attachment",
        "md5": md5,
    }
    if content_type is not None:
        data["contentType"] = content_type
    if link_mode is not None:
        data["linkMode"] = link_mode
    if date_added is not None:
        data["dateAdded"] = date_added
    return {"key": key, "data": data}


def test_get_item_fulltext_reports_lookup_error_with_metadata(
    mock_zotero: Any, sample_item: dict[str, Any]
) -> None:
    """A failed zot.children() call keeps metadata and reports a retryable error."""
    mock_zotero.item.return_value = sample_item
    mock_zotero.children.side_effect = RuntimeError("connection timed out")

    result = get_item_fulltext("ABCD1234")

    assert "Test Article" in result
    assert "10.1234/test" in result
    assert "Couldn't list attachments: connection timed out" in result
    assert "Metadata above is complete; retry for full text" in result
    assert "No suitable attachment found" not in result


def test_lookup_attachment_details_records_exception_type_when_message_empty(
    mock_zotero: Any, sample_item: dict[str, Any]
) -> None:
    """Lookup errors with empty str() still record the exception class name."""

    class SilentTimeoutError(Exception):
        pass

    mock_zotero.children.side_effect = SilentTimeoutError()

    outcome = lookup_attachment_details(mock_zotero, sample_item)

    assert outcome.attachment is None
    assert outcome.error == "SilentTimeoutError"


def test_get_attachment_details_does_not_pick_supplement_by_md5(
    mock_zotero: Any, sample_item: dict[str, Any]
) -> None:
    """Attachment selection must not rank files by their MD5 hash."""
    main_pdf = _child_attachment("MAINPDF1", md5="0a1b2c3d4e")
    supplement_pdf = _child_attachment("SUPPLEM2", md5="f0e1d2c3b4")
    mock_zotero.children.return_value = [main_pdf, supplement_pdf]

    details = get_attachment_details(mock_zotero, sample_item)

    assert details == AttachmentDetails(key="MAINPDF1", content_type="application/pdf")


def test_get_attachment_details_prefers_imported_file_then_earliest_date(
    mock_zotero: Any, sample_item: dict[str, Any]
) -> None:
    """Deterministic ordering prefers imported_file, then earliest dateAdded."""
    linked = _child_attachment(
        "LINKED1",
        md5="ffff",
        link_mode="linked_url",
        date_added="2023-01-01T00:00:00Z",
    )
    later_imported = _child_attachment(
        "LATER2",
        md5="eeee",
        link_mode="imported_file",
        date_added="2024-06-01T00:00:00Z",
    )
    earlier_imported = _child_attachment(
        "EARLY3",
        md5="0001",
        link_mode="imported_file",
        date_added="2024-01-15T00:00:00Z",
    )
    mock_zotero.children.return_value = [linked, later_imported, earlier_imported]

    details = get_attachment_details(mock_zotero, sample_item)

    assert details == AttachmentDetails(key="EARLY3", content_type="application/pdf")


def test_get_attachment_details_prefers_pdf_over_html_and_other(
    mock_zotero: Any, sample_item: dict[str, Any]
) -> None:
    """Content type priority (PDF > HTML > other) outweighs linkMode or date."""
    html = _child_attachment(
        "HTML1",
        content_type="text/html",
        link_mode="imported_file",
        date_added="2020-01-01T00:00:00Z",
    )
    pdf = _child_attachment(
        "PDF1",
        content_type="application/pdf",
        link_mode="imported_url",
        date_added="2025-01-01T00:00:00Z",
    )
    mock_zotero.children.return_value = [html, pdf]

    details = get_attachment_details(mock_zotero, sample_item)

    assert details == AttachmentDetails(key="PDF1", content_type="application/pdf")


def test_get_attachment_details_tolerates_missing_content_type_and_skips_keyless(
    mock_zotero: Any, sample_item: dict[str, Any]
) -> None:
    """Attachments missing contentType normalize to empty string; missing keys skip."""
    keyless = {"key": "", "data": {"itemType": "attachment"}}
    no_ct = _child_attachment("OTHER1", content_type=None)
    mock_zotero.children.return_value = [keyless, no_ct]

    details = get_attachment_details(mock_zotero, sample_item)

    assert details == AttachmentDetails(key="OTHER1", content_type="")
