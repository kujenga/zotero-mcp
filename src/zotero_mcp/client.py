import logging
import os
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


def get_attachment_details(
    zot: zotero.Zotero,
    item: dict[str, Any],
) -> AttachmentDetails | None:
    """Get attachment ID and content type for a Zotero item"""
    data = item.get("data", {})
    item_type = data.get("itemType")

    # Direct attachment - check if it's a PDF or other supported type
    if item_type == "attachment":
        content_type = data.get("contentType")
        return AttachmentDetails(
            key=data.get("key"),
            content_type=content_type,
        )

    # For regular items, look for child attachments
    try:
        children: Any = zot.children(data.get("key", ""))
        # Group attachments by content type and size
        pdfs = []
        htmls = []
        others = []

        for child in children:
            child_data = child.get("data", {})
            if child_data.get("itemType") == "attachment":
                content_type = child_data.get("contentType")
                file_size = child_data.get("md5", "")  # Use md5 as proxy for size

                if content_type == "application/pdf":
                    pdfs.append((child_data.get("key"), content_type, file_size))
                elif content_type == "text/html":
                    htmls.append((child_data.get("key"), content_type, file_size))
                else:
                    others.append((child_data.get("key"), content_type, file_size))

        # Return first match in priority order
        if pdfs:
            pdfs.sort(key=lambda x: x[2], reverse=True)
            return AttachmentDetails(
                key=pdfs[0][0],
                content_type=pdfs[0][1],
            )
        if htmls:
            htmls.sort(key=lambda x: x[2], reverse=True)
            return AttachmentDetails(
                key=htmls[0][0],
                content_type=htmls[0][1],
            )
        if others:
            others.sort(key=lambda x: x[2], reverse=True)
            return AttachmentDetails(
                key=others[0][0],
                content_type=others[0][1],
            )
    except Exception:
        # Best-effort lookup: callers treat a missing attachment as a normal
        # outcome, so log for diagnosis rather than surfacing the failure and
        # losing the metadata we can still return.
        logger.debug(
            "Failed to resolve attachments for item %s",
            data.get("key", ""),
            exc_info=True,
        )

    return None
