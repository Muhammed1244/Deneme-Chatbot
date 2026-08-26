import fitz  # PyMuPDF
import json
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
PDF_DIR = BASE_DIR / "Belgeler"
OUTPUT_DIR = BASE_DIR / "clean_data"
OUTPUT_DIR.mkdir(exist_ok=True)
OUTPUT_FILE = OUTPUT_DIR / "dataset_structured.json"

# Stricter regex ensuring Madde is a standalone header (followed by number and separator)
MADDE_HEADER_PATTERN = re.compile(
    r"^(MADDE|Madde)\s+(\d+)\s*[\–\-—:]?\s*(.*)$"
)
SUB_ITEM_PATTERN = re.compile(
    r"^(\([a-zçğıöşü\d]+\)|[a-zçğıöşü\d]+\)|[a-zçğıöşü]\-|\d+\-|\d+\.)\s+",
    re.IGNORECASE
)

# Common noise patterns in Turkish official legal documents
NOISE_PATTERNS = [
    re.compile(r"^Resmî\s+Gazete\s+Tarihi:.*", re.IGNORECASE),
    re.compile(r"^Sayfa\s+\d+/\d+.*", re.IGNORECASE),
    re.compile(r"^\d+\s*$"),  # Standalone page numbers
]


def is_noise(line_text: str) -> bool:
    """Detects running headers, footers, and page numbers."""
    line = line_text.strip()
    if not line:
        return True
    return any(pattern.match(line) for pattern in NOISE_PATTERNS)


def extract_clean_page_text(page) -> str:
    """Extracts page text, fixes hyphenation/line wraps, and bolds headers."""
    page_dict = page.get_text("dict")
    raw_lines = []

    for block in page_dict.get("blocks", []):
        if "lines" not in block:
            continue
        for line in block["lines"]:
            spans_text = "".join(span.get("text", "") for span in line.get("spans", []))
            clean_line = spans_text.strip()

            if not is_noise(clean_line):
                raw_lines.append(clean_line)

    if not raw_lines:
        return ""

    # Reconstruct continuous flow and fix hyphenation
    formatted_blocks = []
    current_buffer = []

    for line in raw_lines:
        # Check for standalone Article Header
        madde_match = MADDE_HEADER_PATTERN.match(line)
        if madde_match:
            # Flush previous buffer
            if current_buffer:
                formatted_blocks.append(" ".join(current_buffer))
                current_buffer = []
            
            art_num = madde_match.group(2)
            rest_of_title = madde_match.group(3)
            formatted_blocks.append(f"\n**MADDE {art_num}** {rest_of_title}".strip())
            continue

        # Fix hyphenated words at line wraps (e.g., "deniz-" + "cilik" -> "denizcilik")
        if current_buffer and current_buffer[-1].endswith("-"):
            current_buffer[-1] = current_buffer[-1][:-1] + line
        else:
            current_buffer.append(line)

    if current_buffer:
        formatted_blocks.append(" ".join(current_buffer))

    return "\n".join(formatted_blocks)


def process_pdf(pdf_path: Path) -> list[dict]:
    print("Processing & Cleaning:", pdf_path.name)
    page_chunks = []

    with fitz.open(pdf_path) as doc:
        for page in doc:
            page_no = page.number + 1
            cleaned_text = extract_clean_page_text(page)

            if not cleaned_text.strip():
                continue

            # Inject document scope header directly into text payload
            doc_context_header = f"[Belge: {pdf_path.name} | Sayfa: {page_no}]\n"
            final_text = doc_context_header + cleaned_text

            page_chunks.append({
                "source_file": pdf_path.name,
                "page_start": page_no,
                "page_end": page_no,
                "text": final_text
            })

    return page_chunks


def build_dataset():
    dataset = []
    pdfs = sorted(PDF_DIR.glob("*.pdf"))
    print(f"Found {len(pdfs)} PDF files.\n")

    for pdf in pdfs:
        try:
            chunks = process_pdf(pdf)
            dataset.extend(chunks)
        except Exception as e:
            print("FAILED to process:", pdf.name, e)

    return dataset


if __name__ == "__main__":
    dataset = build_dataset()
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(dataset, f, ensure_ascii=False, indent=2)
    print(f"\nUnified dataset created! Total Clean Page Chunks: {len(dataset)}")