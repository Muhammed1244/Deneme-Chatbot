import json
from pathlib import Path
import fitz

PDF_DIR = Path("Belgeler")
DATASET = Path("clean_data/dataset_structured.json")

# -------------------------------------------------
# Read PDFs
# -------------------------------------------------

pdf_info = {}

for pdf in sorted(PDF_DIR.glob("*.pdf")):

    doc = fitz.open(pdf)

    text = ""

    for page in doc:
        text += page.get_text("text")

    pdf_info[pdf.stem] = {
        "pages": len(doc),
        "chars": len(text)
    }

# -------------------------------------------------
# Read dataset
# -------------------------------------------------

with open(DATASET, encoding="utf-8") as f:
    dataset = json.load(f)

dataset_chars = {}

for item in dataset:

    doc = item["document_id"]

    dataset_chars.setdefault(doc, 0)

    dataset_chars[doc] += len(item["text"])

# -------------------------------------------------
# Report
# -------------------------------------------------

print("=" * 105)
print(
    f'{"Document":30}'
    f'{"Pages":>8}'
    f'{"PDF Chars":>15}'
    f'{"Dataset Chars":>18}'
    f'{"Ratio":>10}'
)
print("=" * 105)

for doc in sorted(pdf_info):

    pages = pdf_info[doc]["pages"]
    pdf_chars = pdf_info[doc]["chars"]
    ds_chars = dataset_chars.get(doc, 0)

    ratio = ds_chars / pdf_chars if pdf_chars else 0

    print(
        f"{doc[:30]:30}"
        f"{pages:8}"
        f"{pdf_chars:15,}"
        f"{ds_chars:18,}"
        f"{ratio:10.2f}"
    )

print("=" * 105)