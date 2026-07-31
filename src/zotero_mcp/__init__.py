import re
from typing import Annotated, Any, Literal

from mcp.server import MCPServer
from pydantic import Field

from zotero_mcp.client import get_attachment_details, get_zotero_client

# Create an MCP server
mcp = MCPServer("Zotero")

# Zotero's local API omits empty fields while the web API returns them as "",
# so every field lookup below treats absent and empty alike. That also keeps
# rendering tolerant of older Zotero versions, whose schemas simply lack the
# newer fields: citationKey only became available on nearly every item type in
# the Zotero 8 era (before that just preprint/dataset/standard), and PMID/PMCID
# arrived alongside it. Nothing here requires a field to exist.

# Pinned Better BibTeX keys live in the Extra field as "Citation Key: foo2020bar"
# on Zotero 7 and earlier. Zotero 8 promoted citationKey to a native field and
# migrated those keys, so the native field wins when both are present.
CITATION_KEY_IN_EXTRA = re.compile(
    r"^Citation Key:\s*(\S+)\s*$", re.MULTILINE | re.IGNORECASE
)

# Venue fields ordered most- to least-specific: the first one present is the
# item's source of record. Without this, anything that isn't a journal article
# loses its provenance -- a preprint wouldn't report arXiv, a conference paper
# wouldn't report its proceedings.
SOURCE_FIELDS = (
    "publicationTitle",
    "bookTitle",
    "proceedingsTitle",
    "encyclopediaTitle",
    "dictionaryTitle",
    "websiteTitle",
    "blogTitle",
    "forumTitle",
    "programTitle",
    "conferenceName",
    "repository",
    "institution",
    "university",
    "publisher",
)

# Grouped rendering for the full metadata view. Any populated field missing from
# this table still appears under "Other Fields", so fields from newer Zotero
# schema versions surface without a code change here.
FIELD_SECTIONS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "Publication",
        (
            "publicationTitle",
            "bookTitle",
            "proceedingsTitle",
            "conferenceName",
            "encyclopediaTitle",
            "dictionaryTitle",
            "websiteTitle",
            "websiteType",
            "blogTitle",
            "forumTitle",
            "postType",
            "programTitle",
            "network",
            "repository",
            "repositoryLocation",
            "institution",
            "university",
            "thesisType",
            "publisher",
            "place",
            "edition",
            "series",
            "seriesTitle",
            "seriesNumber",
            "seriesText",
            "volume",
            "numberOfVolumes",
            "issue",
            "section",
            "pages",
            "numPages",
            "journalAbbreviation",
            "reportNumber",
            "reportType",
            "medium",
            "runningTime",
        ),
    ),
    (
        "Identifiers",
        (
            "url",
            "DOI",
            "ISBN",
            "ISSN",
            "PMID",
            "PMCID",
            "archiveID",
            "callNumber",
        ),
    ),
    (
        "Timestamps",
        (
            "dateAdded",
            "dateModified",
            "accessDate",
            "lastRead",
            "filingDate",
            "priorityDate",
        ),
    ),
    (
        "Library",
        (
            "libraryCatalog",
            "archive",
            "archiveLocation",
            "rights",
            "language",
            "shortTitle",
        ),
    ),
    (
        "File",
        (
            "contentType",
            "filename",
            "linkMode",
            "charset",
            "md5",
            "mtime",
            "path",
        ),
    ),
)

# Labels that camelCase splitting alone would get wrong or render awkwardly.
FIELD_LABELS = {
    "url": "URL",
    "publicationTitle": "Publication",
    "numPages": "Number of Pages",
    "numberOfVolumes": "Number of Volumes",
    "accessDate": "Accessed",
    "archiveID": "Archive ID",
    "md5": "MD5",
    "mtime": "File Modified",
}

SECTIONED_FIELDS = frozenset(field for _, fields in FIELD_SECTIONS for field in fields)

# Fields with dedicated rendering, excluded from the "Other Fields" catch-all.
SPECIAL_FIELDS = frozenset(
    {
        "key",
        "version",
        "itemType",
        "title",
        "date",
        "citationKey",
        "creators",
        "abstractNote",
        "tags",
        "extra",
        "note",
        "parentItem",
        "relations",
        "collections",
        "annotationType",
        "annotationText",
        "annotationComment",
        "annotationColor",
        "annotationPageLabel",
        "annotationAuthorName",
        "annotationSortIndex",
        "annotationPosition",
    }
)


def get_citation_key(data: dict[str, Any]) -> str | None:
    """Get an item's citation key, falling back to a Better BibTeX pinned key"""
    if citation_key := data.get("citationKey"):
        return citation_key
    if match := CITATION_KEY_IN_EXTRA.search(data.get("extra", "")):
        return match.group(1)
    return None


def get_source(data: dict[str, Any]) -> str | None:
    """Get the item's source of record, e.g. its journal, book, or repository"""
    for field in SOURCE_FIELDS:
        if value := data.get(field):
            return f"In: {value}" if field == "bookTitle" else value
    return None


def field_label(field: str) -> str:
    """Get the display label for a Zotero field name"""
    if label := FIELD_LABELS.get(field):
        return label
    if field.isupper():
        return field
    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", field)
    return spaced[0].upper() + spaced[1:]


def format_fields(data: dict[str, Any], fields: Any) -> list[str]:
    """Render populated fields as label/value lines, skipping empty ones"""
    return [
        f"{field_label(field)}: {data[field]}" for field in fields if data.get(field)
    ]


def strip_note_html(note: str) -> str:
    """Convert Zotero's HTML note content to rough markdown"""
    note = note.replace("<p>", "").replace("</p>", "\n").replace("<br>", "\n")
    note = note.replace("<strong>", "**").replace("</strong>", "**")
    return note.replace("<em>", "*").replace("</em>", "*")


def format_tags(data: dict[str, Any]) -> str | None:
    """Render an item's tags as a markdown section"""
    if not (tags := data.get("tags")):
        return None
    return "\n### Tags\n" + ", ".join(f"`{tag['tag']}`" for tag in tags)


def format_note(item: dict[str, Any]) -> str:
    """Format a Zotero note item"""
    data = item["data"]

    formatted = [
        "## 📝 Note",
        f"Item Key: `{item['key']}`",
    ]
    if parent_item := data.get("parentItem"):
        formatted.append(f"Parent Item: `{parent_item}`")
    if date := data.get("dateModified"):
        formatted.append(f"Last Modified: {date}")
    if tags := format_tags(data):
        formatted.append(tags)

    formatted.append(f"\n### Note Content\n{strip_note_html(data.get('note', ''))}")

    return "\n".join(formatted)


def format_annotation(item: dict[str, Any]) -> str:
    """Format a Zotero annotation item, i.e. a PDF highlight or comment"""
    data = item["data"]
    annotation_type = data.get("annotationType", "annotation")

    formatted = [
        f"## 🖍 {annotation_type.capitalize()} Annotation",
        f"Item Key: `{item['key']}`",
    ]
    if parent_item := data.get("parentItem"):
        formatted.append(f"Parent Item: `{parent_item}`")
    if page := data.get("annotationPageLabel"):
        formatted.append(f"Page: {page}")
    if color := data.get("annotationColor"):
        formatted.append(f"Color: {color}")
    if author := data.get("annotationAuthorName"):
        formatted.append(f"Author: {author}")
    if date := data.get("dateModified"):
        formatted.append(f"Last Modified: {date}")
    if tags := format_tags(data):
        formatted.append(tags)

    if text := data.get("annotationText"):
        formatted.append(f"\n### Highlighted Text\n{text}")
    if comment := data.get("annotationComment"):
        formatted.append(f"\n### Comment\n{comment}")

    return "\n".join(formatted)


def format_item(item: dict[str, Any]) -> str:
    """Format a Zotero item's full metadata as a string optimized for LLM consumption"""
    data = item["data"]
    item_type = data.get("itemType", "unknown")

    if item_type == "note":
        return format_note(item)
    if item_type == "annotation":
        return format_annotation(item)

    # Identity first: the item key addresses the item through this API, the
    # citation key addresses it from a manuscript.
    formatted = [f"## {data.get('title', 'Untitled')}", f"Item Key: `{item['key']}`"]
    if citation_key := get_citation_key(data):
        formatted.append(f"Citation Key: `{citation_key}`")
    formatted += [
        f"Type: {item_type}",
        f"Date: {data.get('date', 'No date')}",
    ]

    # Creators with role differentiation
    creators_by_role: dict[str, list[str]] = {}
    for creator in data.get("creators", []):
        role = creator.get("creatorType", "contributor")
        name = ""
        if "firstName" in creator and "lastName" in creator:
            name = f"{creator['lastName']}, {creator['firstName']}"
        elif "name" in creator:
            name = creator["name"]

        if name:
            creators_by_role.setdefault(role, []).append(name)

    for role, names in creators_by_role.items():
        role_display = role.capitalize() + ("s" if len(names) > 1 else "")
        formatted.append(f"{role_display}: {'; '.join(names)}")

    if abstract := data.get("abstractNote"):
        formatted.append(f"\n### Abstract\n{abstract}")

    if tags := format_tags(data):
        formatted.append(tags)

    for heading, fields in FIELD_SECTIONS:
        if lines := format_fields(data, fields):
            formatted.append(f"\n### {heading}\n" + "\n".join(lines))

    # Extra holds free-form metadata, including CSL variables and (on Zotero 7
    # and earlier) the pinned citation key already surfaced above.
    if extra := data.get("extra"):
        formatted.append(f"\n### Extra\n{extra}")

    # Catch-all so fields from newer schema versions are never silently dropped.
    unrendered = sorted(set(data) - SECTIONED_FIELDS - SPECIAL_FIELDS)
    if lines := format_fields(data, unrendered):
        formatted.append("\n### Other Fields\n" + "\n".join(lines))

    additional = []
    if num_children := item.get("meta", {}).get("numChildren"):
        additional.append(f"Number of notes/attachments: {num_children}")
    if parsed_date := item.get("meta", {}).get("parsedDate"):
        additional.append(f"Parsed Date: {parsed_date}")
    if parent_item := data.get("parentItem"):
        additional.append(f"Parent Item: `{parent_item}`")
    if collections := data.get("collections"):
        additional.append(
            "Collections: " + ", ".join(f"`{key}`" for key in collections)
        )
    if library_name := item.get("library", {}).get("name"):
        additional.append(f"Library: {library_name}")
    if version := data.get("version"):
        additional.append(f"Version: {version}")
    if additional:
        formatted.append("\n### Additional Information\n" + "\n".join(additional))

    return "\n".join(formatted)


@mcp.tool(
    name="zotero_item_metadata",
    description="Get the complete metadata for a specific Zotero item, given the item key. Includes the citation key, publication details, identifiers, and timestamps.",
)
def get_item_metadata(item_key: str) -> str:
    """Get metadata information about a specific Zotero item"""
    zot = get_zotero_client()

    try:
        item: Any = zot.item(item_key)
        if not item:
            return f"No item found with key: {item_key}"
        return format_item(item)
    # Broad catch is deliberate at an MCP tool boundary: an escaping exception
    # aborts the tool call, whereas an error string lets the model see what
    # went wrong and recover.
    except Exception as e:  # noqa: BLE001
        return f"Error retrieving item metadata: {e!s}"


@mcp.tool(
    name="zotero_item_fulltext",
    description="Get the full text content of a Zotero item, given the item key of a parent item or specific attachment.",
)
def get_item_fulltext(item_key: str) -> str:
    """Get the full text content of a specific Zotero item"""
    zot = get_zotero_client()

    try:
        item: Any = zot.item(item_key)
        if not item:
            return f"No item found with key: {item_key}"

        # Fetch full-text content
        attachment = get_attachment_details(zot, item)

        # Prepare header with metadata
        header = format_item(item)

        # Add attachment information
        if attachment is not None:
            attachment_info = f"\n## Attachment Information\n- **Key**: `{attachment.key}`\n- **Type**: {attachment.content_type}"

            # Get the full text
            full_text_data: Any = zot.fulltext_item(attachment.key)
            if full_text_data and "content" in full_text_data:
                item_text = full_text_data["content"]
                # Calculate approximate word count
                word_count = len(item_text.split())
                attachment_info += f"\n- **Word Count**: ~{word_count}"

                # Format the content with markdown for structure
                full_text = f"\n\n## Document Content\n\n{item_text}"
            else:
                # Clear error message when text extraction isn't possible
                full_text = "\n\n## Document Content\n\n[⚠️ Attachment is available but text extraction is not possible. The document may be scanned as images or have other restrictions that prevent text extraction.]"
        else:
            attachment_info = "\n\n## Attachment Information\n[❌ No suitable attachment found for full text extraction. This item may not have any attached files or they may not be in a supported format.]"
            full_text = ""

        # Combine all sections
        return f"{header}{attachment_info}{full_text}"

    # See get_item_metadata: errors are reported to the caller, not raised.
    except Exception as e:  # noqa: BLE001
        return f"Error retrieving item full text: {e!s}"


# Search behaviour below was verified against both a local Zotero API and
# api.zotero.org rather than taken from the docs, which are thin and in one
# respect outdated: https://www.zotero.org/support/dev/web_api/v3/basics#searching
# says quick search "currently supports phrase searching only", but both APIs
# actually match items containing all the query's words in any position.
@mcp.tool(
    name="zotero_search_items",
    description=(
        "Search for items in your Zotero library. Returns a summary of each match; "
        "look up individual results with zotero_item_metadata or zotero_item_fulltext."
        "\n\n"
        "Choosing a query mode:\n"
        "- 'titleCreatorYear' (the default) searches titles, creator names, and years. "
        "Use it for known-item lookup, where you know roughly what the item is called "
        "or who wrote it.\n"
        "- 'everything' additionally searches abstracts, the Extra field, note text, "
        "and the full text of attachments. Use it for topic and full-text search, "
        "where the term would not appear in a title.\n\n"
        "Words match by prefix and multi-word queries match items containing all of "
        "the words in any position, so 'cybor insect' matches 'Cyborg Insect'."
    ),
)
def search_items(
    query: Annotated[
        str,
        Field(
            description=(
                "Text to match. Words match by prefix, and an item must contain every "
                "word in the query, though not necessarily as a contiguous phrase."
            )
        ),
    ],
    qmode: Annotated[
        Literal["titleCreatorYear", "everything"] | None,
        Field(
            description=(
                "Which fields to search. 'titleCreatorYear' covers titles, creator "
                "names, and years; against a local Zotero API it also matches citation "
                "keys, which the Zotero Web API does not index. 'everything' adds "
                "abstracts, the Extra field, note text, and attachment full text, so "
                "use it to find work by what is written inside the PDF rather than in "
                "its metadata. A match inside an attachment or note is returned as "
                "that child item rather than as its parent, so results routinely "
                "contain more entries than distinct works."
            )
        ),
    ] = "titleCreatorYear",
    tag: Annotated[
        str | None,
        Field(
            description=(
                "Filter by tag. Use 'foo || bar' to match either tag and '-foo' to "
                "exclude one; tag names containing spaces are matched as written. "
                "Requiring two tags at once is not expressible here."
            )
        ),
    ] = None,
    limit: Annotated[
        int | None,
        Field(
            description=(
                "Maximum number of results. Worth raising when qmode is 'everything', "
                "where several attachments or notes belonging to one work can each "
                "match separately."
            )
        ),
    ] = 10,
) -> str:
    """Search for items in your Zotero library"""
    zot = get_zotero_client()

    # Search using the q parameter
    params = {"q": query, "qmode": qmode, "limit": limit}
    if tag:
        params["tag"] = tag

    zot.add_parameters(**params)
    # n.b. types for this return do not work, it's a parsed JSON object
    results: Any = zot.items()

    if not results:
        return "No items found matching your query."

    # Header with search info
    header = [
        f"# Search Results for: '{query}'",
        f"Found {len(results)} items." + (f" Using tag filter: {tag}" if tag else ""),
        "Use item keys with zotero_item_metadata or zotero_item_fulltext for more details.\n",
    ]

    # Format results
    formatted_results = []
    for i, item in enumerate(results):
        data = item["data"]
        item_key = item.get("key", "")
        item_type = data.get("itemType", "unknown")

        # Special handling for notes
        if item_type == "note":
            note_content = strip_note_html(data.get("note", ""))

            # Extract a title from the first line if possible, otherwise use first few words
            title_preview = ""
            if note_content:
                lines = note_content.strip().split("\n")
                first_line = lines[0].strip()
                if first_line:
                    # Use first line if it's reasonably short, otherwise use first few words
                    if len(first_line) <= 50:
                        title_preview = first_line
                    else:
                        words = first_line.split()
                        title_preview = " ".join(words[:5]) + "..."

            # Create a good title for the note
            note_title = title_preview if title_preview else "Note"

            # Get a preview of the note content (truncated)
            preview = note_content.strip()
            if len(preview) > 150:
                preview = preview[:147] + "..."

            # Format the note entry
            entry = [
                f"## {i + 1}. 📝 {note_title}",
                f"**Type**: Note | **Key**: `{item_key}`",
                f"\n{preview}",
            ]

            # Add parent item reference if available
            if parent_item := data.get("parentItem"):
                entry.insert(2, f"**Parent Item**: `{parent_item}`")

            # Add tags if present (limited to first 5)
            if tags := data.get("tags"):
                tag_list = [f"`{tag['tag']}`" for tag in tags[:5]]
                if len(tags) > 5:
                    tag_list.append("...")
                entry.append(f"\n**Tags**: {' '.join(tag_list)}")

            formatted_results.append("\n".join(entry))
            continue

        # Regular item processing (non-notes)
        title = data.get("title", "Untitled")
        date = data.get("date", "")

        # Format primary creators (limited to first 3)
        creators = []
        for creator in data.get("creators", [])[:3]:
            if "firstName" in creator and "lastName" in creator:
                creators.append(f"{creator['lastName']}, {creator['firstName']}")
            elif "name" in creator:
                creators.append(creator["name"])

        if len(data.get("creators", [])) > 3:
            creators.append("et al.")

        creator_str = "; ".join(creators) if creators else "No authors"

        # Get a brief abstract (truncated if too long)
        abstract = data.get("abstractNote", "")
        if len(abstract) > 150:
            abstract = abstract[:147] + "..."

        # Build formatted entry with markdown for better structure
        key_line = f"**Type**: {item_type} | **Date**: {date} | **Key**: `{item_key}`"
        if citation_key := get_citation_key(data):
            key_line += f" | **Citation Key**: `{citation_key}`"
        entry = [
            f"## {i + 1}. {title}",
            key_line,
            f"**Authors**: {creator_str}",
        ]

        if source := get_source(data):
            entry.append(f"**Source**: {source}")

        if abstract:
            entry.append(f"\n{abstract}")

        # Add tags if present (limited to first 5)
        if tags := data.get("tags"):
            tag_list = [f"`{tag['tag']}`" for tag in tags[:5]]
            if len(tags) > 5:
                tag_list.append("...")
            entry.append(f"\n**Tags**: {' '.join(tag_list)}")

        formatted_results.append("\n".join(entry))

    return "\n\n".join(header + formatted_results)
