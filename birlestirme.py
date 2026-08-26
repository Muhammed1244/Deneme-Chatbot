import fitz
from pathlib import Path

# ==========================================================
# PATHS
# ==========================================================

BASE_DIR = Path(__file__).resolve().parent

INPUT_DIR = BASE_DIR / "Yenidosyalar" / "Uygulama Talimatları"

OUTPUT_FILE = BASE_DIR / "Yenidosyalar" / "Uygulama_Talimatlari.pdf"

# ==========================================================
# MERGE PDFs
# ==========================================================

def merge_pdfs():

    pdf_files = sorted(INPUT_DIR.glob("*.pdf"))

    if not pdf_files:
        print("No PDF files found.")
        return

    merged = fitz.open()

    print(f"Found {len(pdf_files)} PDF files.\n")

    for pdf in pdf_files:

        print(f"Adding: {pdf.name}")

        with fitz.open(pdf) as doc:
            merged.insert_pdf(doc)

    merged.save(
        OUTPUT_FILE,
        garbage=4,
        deflate=True
    )

    merged.close()

    print("\n===================================")
    print("Merge completed successfully.")
    print(f"Output: {OUTPUT_FILE}")
    print("===================================")

# ==========================================================
# MAIN
# ==========================================================

if __name__ == "__main__":

    merge_pdfs()