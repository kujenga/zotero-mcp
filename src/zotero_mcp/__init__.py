from typing import Any, Literal

from mcp.server.fastmcp import FastMCP

from zotero_mcp.client import get_attachment_details, get_zotero_client

# Create an MCP server
mcp = FastMCP("Zotero")


def format_item(item: dict[str, Any]) -> str:
    """Format a Zotero item's metadata as a readable string optimized for LLM consumption"""
    data = item["data"]
    item_key = item["key"]
    item_type = data.get("itemType", "unknown")
    
    # Special handling for notes
    if item_type == "note":
        # Get note content
        note_content = data.get("note", "")
        # Strip HTML tags for cleaner text (simple approach)
        note_content = note_content.replace("<p>", "").replace("</p>", "\n").replace("<br>", "\n")
        note_content = note_content.replace("<strong>", "**").replace("</strong>", "**")
        note_content = note_content.replace("<em>", "*").replace("</em>", "*")
        
        # Format note with clear sections
        formatted = [
            "## 📝 Note",
            f"Item Key: `{item_key}`",
        ]
        
        # Add parent item reference if available
        if parent_item := data.get("parentItem"):
            formatted.append(f"Parent Item: `{parent_item}`")
        
        # Add date if available
        if date := data.get("dateModified"):
            formatted.append(f"Last Modified: {date}")
        
        # Add tags with formatting for better visibility
        if tags := data.get("tags"):
            tag_list = [f"`{tag['tag']}`" for tag in tags]
            formatted.append(f"\n### Tags\n{', '.join(tag_list)}")
        
        # Add note content
        formatted.append(f"\n### Note Content\n{note_content}")
        
        return "\n".join(formatted)
    
    # Regular item handling (non-notes)
    
    # Basic metadata with key for easy reference
    formatted = [
        f"## {data.get('title', 'Untitled')}",
        f"Item Key: `{item_key}`",
        f"Type: {item_type}",
        f"Date: {data.get('date', 'No date')}",
    ]

    # Creators with role differentiation
    creators_by_role = {}
    for creator in data.get("creators", []):
        role = creator.get("creatorType", "contributor")
        name = ""
        if "firstName" in creator and "lastName" in creator:
            name = f"{creator['lastName']}, {creator['firstName']}"
        elif "name" in creator:
            name = creator["name"]

        if name:
            if role not in creators_by_role:
                creators_by_role[role] = []
            creators_by_role[role].append(name)

    for role, names in creators_by_role.items():
        role_display = role.capitalize() + ("s" if len(names) > 1 else "")
        formatted.append(f"{role_display}: {'; '.join(names)}")

    # Publication details
    if publication := data.get("publicationTitle"):
        formatted.append(f"Publication: {publication}")
    if volume := data.get("volume"):
        volume_info = f"Volume: {volume}"
        if issue := data.get("issue"):
            volume_info += f", Issue: {issue}"
        if pages := data.get("pages"):
            volume_info += f", Pages: {pages}"
        formatted.append(volume_info)

    # Abstract with clear section header
    if abstract := data.get("abstractNote"):
        formatted.append(f"\n### Abstract\n{abstract}")

    # Tags with formatting for better visibility
    if tags := data.get("tags"):
        tag_list = [f"`{tag['tag']}`" for tag in tags]
        formatted.append(f"\n### Tags\n{', '.join(tag_list)}")

    # URLs, DOIs, and identifiers grouped together
    identifiers = []
    if url := data.get("url"):
        identifiers.append(f"URL: {url}")
    if doi := data.get("DOI"):
        identifiers.append(f"DOI: {doi}")
    if isbn := data.get("ISBN"):
        identifiers.append(f"ISBN: {isbn}")
    if issn := data.get("ISSN"):
        identifiers.append(f"ISSN: {issn}")

    if identifiers:
        formatted.append("\n### Identifiers\n" + "\n".join(identifiers))

    # Notes and attachments
    if notes := item.get("meta", {}).get("numChildren", 0):
        formatted.append(
            f"\n### Additional Information\nNumber of notes/attachments: {notes}"
        )

    return "\n".join(formatted)


@mcp.tool(
    name="zotero_item_metadata",
    description="Get metadata information about a specific Zotero item, given the item key.",
)
def get_item_metadata(item_key: str) -> str:
    """Get metadata information about a specific Zotero item"""
    zot = get_zotero_client()

    try:
        item: Any = zot.item(item_key)
        if not item:
            return f"No item found with key: {item_key}"
        return format_item(item)
    except Exception as e:
        return f"Error retrieving item metadata: {str(e)}"


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

    except Exception as e:
        return f"Error retrieving item full text: {str(e)}"


@mcp.tool(
    name="zotero_search_items",
    # More detail can be added if useful: https://www.zotero.org/support/dev/web_api/v3/basics#searching
    description="Search for items in your Zotero library, given a query string, query mode (titleCreatorYear or everything), and optional tag search (supports boolean searches). Returned results can be looked up with zotero_item_fulltext or zotero_item_metadata.",
)
def search_items(
    query: str,
    qmode: Literal["titleCreatorYear", "everything"] | None = "titleCreatorYear",
    tag: str | None = None,
    limit: int | None = 10,
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
            # Get note content
            note_content = data.get("note", "")
            # Strip HTML tags for cleaner text (simple approach)
            note_content = note_content.replace("<p>", "").replace("</p>", "\n").replace("<br>", "\n")
            note_content = note_content.replace("<strong>", "**").replace("</strong>", "**")
            note_content = note_content.replace("<em>", "*").replace("</em>", "*")
            
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

        # Get publication or source info
        source = ""
        if pub := data.get("publicationTitle"):
            source = pub
        elif book := data.get("bookTitle"):
            source = f"In: {book}"
        elif publisher := data.get("publisher"):
            source = f"{publisher}"

        # Get a brief abstract (truncated if too long)
        abstract = data.get("abstractNote", "")
        if len(abstract) > 150:
            abstract = abstract[:147] + "..."

        # Build formatted entry with markdown for better structure
        entry = [
            f"## {i + 1}. {title}",
            f"**Type**: {item_type} | **Date**: {date} | **Key**: `{item_key}`",
            f"**Authors**: {creator_str}",
        ]

        if source:
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
