def build_citations(chunks):

    citations = []

    seen = set()

    for c in chunks:

        key = (
            c["source_file"],
            c["page_start"],
            c["page_end"]
        )

        if key in seen:
            continue

        seen.add(key)

        citations.append({
            "source_file": c["source_file"],
            "page_start": c["page_start"],
            "page_end": c["page_end"],
        })

    return citations