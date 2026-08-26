# chunker.py

import re

# ---------------------------------------------------
# Configuration
# ---------------------------------------------------

MAX_WORDS = 220
OVERLAP = 40


# ---------------------------------------------------
# Sentence Splitter
# ---------------------------------------------------

def split_sentences(text):
    """
    Split while keeping punctuation.
    Works reasonably well for Turkish and English.
    """

    sentences = re.split(
        r'(?<=[.!?])\s+',
        text
    )

    return [s.strip() for s in sentences if s.strip()]


# ---------------------------------------------------
# Detect Legal Headings
# ---------------------------------------------------

LEGAL_PATTERNS = [

    r"^CHAPTER\s+[IVXLC0-9]+",

    r"^PART\s+[A-Z0-9]+",

    r"^SECTION\s+[A-Z0-9.\-]+",

    r"^REGULATION\s+\d+",

    r"^RULE\s+\d+",

    r"^ARTICLE\s+\d+",

    r"^MADDE\s+\d+",

    r"^EK\s+[IVXLC0-9]+",

    r"^A-[IVXLC]+/\d+",

    r"^B-[IVXLC]+/\d+",
]


def is_heading(sentence):

    s = sentence.strip().upper()

    for p in LEGAL_PATTERNS:
        if re.match(p, s):
            return True

    return False


# ---------------------------------------------------
# Main Chunker
# ---------------------------------------------------

def legal_chunk(text):

    sentences = split_sentences(text)

    chunks = []

    current = []

    current_words = 0

    chunk_id = 0

    for sentence in sentences:

        words = sentence.split()

        # -------------------------------------------------
        # Start a new chunk if a legal heading appears
        # and current chunk already contains text
        # -------------------------------------------------

        if is_heading(sentence) and current:

            chunks.append({
                "chunk_id": chunk_id,
                "text": " ".join(current)
            })

            chunk_id += 1

            current = []

            current_words = 0

        # -------------------------------------------------
        # If current chunk would exceed limit
        # -------------------------------------------------

        if current_words + len(words) > MAX_WORDS:

            chunks.append({
                "chunk_id": chunk_id,
                "text": " ".join(current)
            })

            chunk_id += 1

            # overlap
            overlap = []

            count = 0

            for s in reversed(current):

                overlap.insert(0, s)

                count += len(s.split())

                if count >= OVERLAP:
                    break

            current = overlap

            current_words = sum(
                len(x.split())
                for x in current
            )

        current.append(sentence)

        current_words += len(words)

    if current:

        chunks.append({
            "chunk_id": chunk_id,
            "text": " ".join(current)
        })

    return chunks