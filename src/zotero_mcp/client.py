import logging
import os
from dataclasses import dataclass
from typing import Any

from dotenv import load_dotenv
from pydantic import BaseModel
from pyzotero import zotero

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


# Initialize Zotero client
def get_zotero_client() -> zotero.Zotero:
    """Get authenticated Zotero client using environment variables"""
    library_id = os.getenv("ZOTERO_LIBRARY_ID")
    library_type = os.getenv("ZOTERO_LIBRARY_TYPE", "user")
    api_key = os.getenv("ZOTERO_API_KEY") or None
    local = os.getenv("ZOTERO_LOCAL", "").lower() in ["true", "yes", "1"]
    if local:
        if not library_id:
            # Indicates "current user" for the local API
            library_id = "0"
    elif not all([library_id, api_key]):
        raise ValueError(
            "Missing required environment variables. Please set ZOTERO_LIBRARY_ID and ZOTERO_API_KEY"
        )

    return zotero.Zotero(
        library_id=library_id,
        library_type=library_type,
        api_key=api_key,
        local=local,
    )


class AttachmentDetails(BaseModel):
    key: str
    content_type: str


@dataclass(frozen=True)
class AttachmentLookup:
    """Outcome of looking up the primary attachment for a Zotero item."""

    attachment: AttachmentDetails | None = None
    error: str | None = None


def _attachment_sort_key(
    child_data: dict[str, Any], index: int
) -> tuple[int, int, str, int]:
    """Rank attachment candidates deterministically without relying on hashes."""
    link_mode_rank = 0 if child_data.get("linkMode") == "imported_file" else 1
    date_added = child_data.get("dateAdded") or ""
    date_rank = 0 if date_added else 1
    return (link_mode_rank, date_rank, date_added, index)


def lookup_attachment_details(
    zot: zotero.Zotero,
    item: dict[str, Any],
) -> AttachmentLookup:
    """Resolve the best attachment for a Zotero item, capturing lookup errors."""
    data = item.get("data", {})
    item_type = data.get("itemType")

    # Direct attachment - check if it's a PDF or other supported type
    if item_type == "attachment":
        content_type = data.get("contentType") or ""
        return AttachmentLookup(
            attachment=AttachmentDetails(
                key=data.get("key"),
                content_type=content_type,
            )
        )

    # For regular items, look for child attachments
    try:
        children: Any = zot.children(data.get("key", ""))
        pdfs: list[tuple[tuple[int, int, str, int], str, str]] = []
        htmls: list[tuple[tuple[int, int, str, int], str, str]] = []
        others: list[tuple[tuple[int, int, str, int], str, str]] = []

        for index, child in enumerate(children):
            child_data = child.get("data", {})
            if child_data.get("itemType") == "attachment":
                key = child_data.get("key")
                if not key:
                    continue
                content_type = child_data.get("contentType") or ""
                candidate = (_attachment_sort_key(child_data, index), key, content_type)

                if content_type == "application/pdf":
                    pdfs.append(candidate)
                elif content_type == "text/html":
                    htmls.append(candidate)
                else:
                    others.append(candidate)

        for bucket in (pdfs, htmls, others):
            if bucket:
                _, key, content_type = min(bucket, key=lambda entry: entry[0])
                return AttachmentLookup(
                    attachment=AttachmentDetails(
                        key=key,
                        content_type=content_type,
                    )
                )
    except Exception as exc:
        # Best-effort lookup: callers still return item metadata, so surface
        # the lookup error separately instead of pretending no attachment exists.
        logger.debug(
            "Failed to resolve attachments for item %s",
            data.get("key", ""),
            exc_info=True,
        )
        error_detail = str(exc) or type(exc).__name__
        return AttachmentLookup(error=error_detail)

    return AttachmentLookup()


def get_attachment_details(
    zot: zotero.Zotero,
    item: dict[str, Any],
) -> AttachmentDetails | None:
    """Get attachment ID and content type for a Zotero item"""
    return lookup_attachment_details(zot, item).attachment
