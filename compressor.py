# compressor.py

from collections import OrderedDict


# ==========================================================
# COMPRESS CONTEXT
# ==========================================================

def compress_context(
    query,
    chunks,
    max_chunks=8,
    max_chars=16000
):
    """
    Formats retrieved chunks into a clean prompt context.

    Parameters
    ----------
    chunks : list
        Retrieved (and preferably reranked) chunks.

    max_chunks : int
        Maximum number of chunks.

    max_chars : int
        Maximum total context length.
    """

    if not chunks:
        return ""

    # ------------------------------------------------------
    # Remove duplicates
    # ------------------------------------------------------

    unique = OrderedDict()

    for chunk in chunks:

        if isinstance(chunk, str):
            continue

        cid = chunk.get("citation_id")

        if cid not in unique:
            unique[cid] = chunk

    context_parts = []

    total_chars = 0

    # ------------------------------------------------------
    # Build context
    # ------------------------------------------------------

    for i, c in enumerate(unique.values()):

        if i >= max_chunks:
            break

        page_start = c.get("page_start", c.get("page", "?"))
        page_end = c.get("page_end", page_start)

        pages = (
            str(page_start)
            if page_start == page_end
            else f"{page_start}-{page_end}"
        )

        chapter = c.get("chapter", "")
        part = c.get("part", "")
        section = c.get("section", "")

        block = f"""### SOURCE {i+1}

Citation ID : {c.get('citation_id','')}

Document    : {c.get('document_title','')}

Source File : {c.get('source_file','')}

Pages       : {pages}

Chapter     : {chapter}

Part        : {part}

Section     : {section}

Content
-------
{c.get('text','')}

"""

        if total_chars + len(block) > max_chars:
            break

        context_parts.append(block)

        total_chars += len(block)

    return "\n".join(context_parts)