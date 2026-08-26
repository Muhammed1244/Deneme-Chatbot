from pathlib import Path
import fitz
import re
import csv

# ==========================================================
# CONFIGURATION
# ==========================================================

PDF_FOLDER = Path("Belgeler")

MAX_SCAN_PAGES = 3

DRY_RUN = True      # False = actually rename files

# ==========================================================
# TURKISH -> ASCII
# ==========================================================

TR_MAP = str.maketrans({
    "ç": "c",
    "Ç": "c",
    "ğ": "g",
    "Ğ": "g",
    "ı": "i",
    "İ": "i",
    "ö": "o",
    "Ö": "o",
    "ş": "s",
    "Ş": "s",
    "ü": "u",
    "Ü": "u",
})

# ==========================================================
# GOOD / BAD WORDS
# ==========================================================

GOOD_PATTERNS = [

      r".+ kanunu$",
    r".+ yönetmeliği$",
    r".+ yönetmelik$",
    r".+ tebliği$",
    r".+ tebliğ$",
    r".+ genelgesi$",
    r".+ genelge$",
    r".+ talimatı$",
    r".+ talimat$",
    r".+ yönergesi$",
    r".+ yönerge$",

    r".*solas.*",
    r".*marpol.*",
    r".*stcw.*",
    r".*mlc.*",
    r".*ism.*",
    r".*isps.*",

    r".*international convention.*",

]

BAD_PATTERNS = [

    "t.c.",
    "tc",

    "resmî gazete",
    "resmi gazete",

    "bakanlığı",
    "bakanligi",

    "sayfa",

    "www",

    "http",

    "isbn",

    "issn",

    "copyright",

]

# ==========================================================
# CLEAN FILENAME
# ==========================================================

def slugify(text):

    text = text.translate(TR_MAP)

    text = text.lower()

    text = re.sub(r"[^\w\s-]", "", text)

    text = re.sub(r"\s+", "_", text)

    text = re.sub(r"_+", "_", text)

    return text.strip("_")


# ==========================================================
# GARBAGE CHECK
# ==========================================================

def is_garbage(text):

    t = text.strip()

    if len(t) < 5:
        return True

    if re.fullmatch(r"\d+", t):
        return True

    if re.fullmatch(r"\d+\.\d+\.\d+", t):
        return True

    if re.fullmatch(r"\d{2}\.\d{2}\.\d{4}", t):
        return True

    if "www" in t.lower():
        return True

    if "http" in t.lower():
        return True

    return False


# ==========================================================
# SCORE LINE
# ==========================================================

def score_line(text, fontsize, y):

    score = 0

    low = text.lower()

    # -----------------------
    # Font size
    # -----------------------

    score += fontsize * 2

    # -----------------------
    # Near top
    # -----------------------

    if y < 120:
        score += 40

    elif y < 220:
        score += 20

    elif y < 350:
        score += 5

    # -----------------------
    # Word count
    # -----------------------

    wc = len(text.split())

    if wc == 1:
        score -= 20

    elif 2 <= wc <= 10:
        score += 20

    elif wc > 25:
        score -= 20

    # -----------------------
    # Good keywords
    # -----------------------

    for word in GOOD_PATTERNS:

        if word in low:

            score += 35

    # -----------------------
    # Bad keywords
    # -----------------------

    for word in BAD_PATTERNS:

        if word in low:

            score -= 50

    # -----------------------
    # Ministry headers
    # -----------------------

    if text.isupper():

        if "BAKANLI" in text:

            score -= 80

    return score


# ==========================================================
# EXTRACT ALL CANDIDATE LINES
# ==========================================================

def extract_candidates(pdf_path):

    candidates = []

    doc = fitz.open(pdf_path)

    pages = min(MAX_SCAN_PAGES, len(doc))

    # Ignore body paragraphs


    for page_index in range(pages):
        

        page = doc[page_index]

        data = page.get_text("dict")

        for block in data["blocks"]:

            if "lines" not in block:
                continue

            for line in block["lines"]:

                text = ""

                fontsize = 0

                y = None

                for span in line["spans"]:

                    text += span["text"]

                    fontsize = max(fontsize, span["size"])

                    if y is None:

                        y = span["bbox"][1]

                text = text.strip()
                if len(text.split()) > 15:
                    continue

                if len(text) > 120:
                    continue

                if is_garbage(text):
                    continue

                score = score_line(
                    text,
                    fontsize,
                    y
                )

                candidates.append({

                    "text": text,

                    "page": page_index + 1,

                    "fontsize": fontsize,

                    "y": y,

                    "score": score

                })

    doc.close()

    return candidates


# ==========================================================
# TITLE DETECTION
# ==========================================================

def detect_title(pdf_path):

    candidates = extract_candidates(pdf_path)

    if not candidates:

        return pdf_path.stem, 0

    candidates.sort(

        key=lambda x: x["score"],

        reverse=True

    )

    best = candidates[0]

    title = best["text"]

    confidence = best["score"]

    # ---------------------------------
    # Merge nearby lines
    # ---------------------------------

    merged = [title]

    for c in candidates[1:8]:

        if c["page"] != best["page"]:
            continue

        if abs(c["fontsize"] - best["fontsize"]) > 2:
            continue

        if abs(c["y"] - best["y"]) > 70:
            continue

        if c["text"] not in merged:

            merged.append(c["text"])

    title = " ".join(merged)

    return title, confidence


# ==========================================================
# CLEAN TITLE
# ==========================================================

def clean_title(title):

    title = re.sub(r"\s+", " ", title)

    title = title.strip()

    # remove duplicated words
    words = title.split()

    cleaned = []

    for w in words:

        if len(cleaned) == 0 or cleaned[-1].lower() != w.lower():

            cleaned.append(w)

    return " ".join(cleaned)


# ==========================================================
# GENERATE SAFE FILENAME
# ==========================================================

def make_filename(title, pdf):

    title = clean_title(title)

    filename = slugify(title)

    if len(filename) < 6:
        filename = slugify(pdf.stem)

    # Windows-safe length
    MAX_LEN = 100

    if len(filename) > MAX_LEN:
        filename = filename[:MAX_LEN].rstrip("_")

    return filename


# ==========================================================
# RENAME PDFs
# ==========================================================

def rename_pdfs():

    pdfs = sorted(PDF_FOLDER.glob("*.pdf"))

    print("=" * 70)
    print(f"Found {len(pdfs)} PDF files")
    print("=" * 70)

    used_names = set()

    log_rows = []

    renamed = 0

    for pdf in pdfs:

        print()

        print("-" * 70)

        print("Processing:", pdf.name)

        title, confidence = detect_title(pdf)

        title = clean_title(title)

        filename = make_filename(title, pdf)

        base = filename

        counter = 2

        while filename in used_names:

            filename = f"{base}_{counter}"

            counter += 1

        used_names.add(filename)

        new_name = filename + ".pdf"

        print("Detected title : ", title)

        print("Confidence     : ", round(confidence, 2))

        print("New filename   : ", new_name)

        if DRY_RUN:

            print("DRY RUN -> not renamed")

        else:

            pdf.rename(pdf.with_name(new_name))

            renamed += 1

        log_rows.append({

            "old": pdf.name,

            "title": title,

            "confidence": round(confidence,2),

            "new": new_name

        })

    save_log(log_rows)

    print()

    print("=" * 70)

    print("Finished")

    print("Renamed:", renamed)

    print("Log file: rename_log.csv")

    print("=" * 70)


# ==========================================================
# SAVE LOG
# ==========================================================

def save_log(rows):

    with open(

        "rename_log.csv",

        "w",

        newline="",

        encoding="utf-8-sig"

    ) as f:

        writer = csv.writer(f)

        writer.writerow([

            "Old Filename",

            "Detected Title",

            "Confidence",

            "New Filename"

        ])

        for r in rows:

            writer.writerow([

                r["old"],

                r["title"],

                r["confidence"],

                r["new"]

            ])


# ==========================================================
# MAIN
# ==========================================================

if __name__ == "__main__":

    rename_pdfs()