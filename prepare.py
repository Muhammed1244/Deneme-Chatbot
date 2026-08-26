import re
import json
from pathlib import Path
import fitz  # PyMuPDF


# =====================================================
# PATHS
# =====================================================

BASE_DIR = Path(__file__).resolve().parent
PDF_DIR = BASE_DIR / "Belgeler"
CLEAN_DIR = BASE_DIR / "clean_data"

OUTPUT_FILE = CLEAN_DIR / "dataset_structured.json"

CLEAN_DIR.mkdir(exist_ok=True)


# =====================================================
# PDF EXTRACTION (PAGE-AWARE)
# =====================================================

def extract_pdf_pages(pdf_path: Path):

    doc = fitz.open(pdf_path)

    pages = []

    for page_num, page in enumerate(doc):

        text = page.get_text("text")

        pages.append({
            "page": page_num + 1,
            "text": text
        })

    return pages


# =====================================================
# CLEAN TEXT
# =====================================================

def clean_text(text):
    text = text.replace("\u200b", " ")
    text = text.replace("\ufeff", "")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()

# =====================================================
# TITLE EXTRACTION
# =====================================================

def extract_document_title(text: str):

    lines = [l.strip() for l in text.splitlines() if l.strip()]

    if not lines:
        return "Unknown Document"

    for line in lines[:25]:

        upper = line.upper()

        if any(k in upper for k in [
            "SOLAS", "STCW", "MARPOL",
            "KANUN", "REGULATION",
            "CONVENTION"
        ]):
            return line[:120]

    return lines[0]


# =====================================================
# SECTION DETECTION (ROBUST)
# =====================================================

def extract_section(text: str):

    patterns = [
        r"\bCHAPTER\s+[IVXLC0-9]+\b",
        r"\bPART\s+[A-Z0-9]+\b",
        r"\bSECTION\s+[0-9A-Z.-]+\b",
        r"\bREGULATION\s+\d+(\.\d+)?\b",
        r"\bRULE\s+\d+(\.\d+)?\b",
        r"\bMADDE\s+\d+(\.\d+)?\b",
        r"\b[A-Z]-[IVXLC]+/\d+(\.\d+)?\b",   # STCW A-II/1
        r"\bARTICLE\s+\d+(\.\d+)?\b"
    ]

    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            return m.group(0)

    return ""


# =====================================================
# CHUNKING
# =====================================================

def chunk_text(text, size=1200, overlap=200):

    chunks = []

    start = 0

    while start < len(text):

        chunk = text[start:start + size]
        chunks.append(chunk)

        start += size - overlap

    return chunks


# =====================================================
# PROCESS SINGLE PDF (CORE ENGINE)
# =====================================================

def process_file(pdf_path: Path):

    pages = extract_pdf_pages(pdf_path)

    dataset = []

    global_chunk_id = 0

    for page in pages:

        page_num = page["page"]

        text = clean_text(page["text"])

        if len(text) < 100:
            continue

        chunks = chunk_text(text)

        for i, chunk in enumerate(chunks):

            citation_id = f"{pdf_path.stem}_p{page_num}_c{i}"

            dataset.append({
                "citation_id": citation_id,

                "document_id": pdf_path.stem,
                "chunk_id": global_chunk_id,

                "page": page_num,

                "document_title": extract_document_title(text),

                "section": extract_section(chunk),

                "source_file": pdf_path.name,

                "text": chunk
            })

            global_chunk_id += 1

    return dataset


# =====================================================
# BUILD DATASET
# =====================================================

def build_dataset():

    dataset = []

    files = sorted(PDF_DIR.glob("*.pdf"))

    print(f"Found {len(files)} PDF files\n")

    for f in files:

        try:
            print("Processing:", f.name)

            chunks = process_file(f)

            dataset.extend(chunks)

            print(f"  -> {len(chunks)} chunks")

        except Exception as e:
            print("Skipped:", f.name)
            print(e)

    return dataset


# =====================================================
# SAVE DATASET
# =====================================================

def save_dataset(dataset):

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(dataset, f, ensure_ascii=False, indent=2)

    print("\n===================================")
    print(f"Saved {len(dataset)} chunks")
    print(OUTPUT_FILE)
    print("===================================")


# =====================================================
# MAIN
# =====================================================

if __name__ == "__main__":

    print("=" * 50)
    print("NEXT LEVEL LEGAL PDF PIPELINE (PAGE-AWARE)")
    print("=" * 50)

    dataset = build_dataset()

    save_dataset(dataset)

    print("\nDONE ✓")