import json
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
INPUT_FILE = BASE_DIR / "clean_data" / "dataset.json"
OUTPUT_FILE = BASE_DIR / "clean_data" / "dataset_structured.json"

# ============================
# DETECT LAW NAME
# ============================
def detect_law(text):

    laws = {
        "SOLAS": ["solas"],
        "MARPOL": ["marpol"],
        "COLREG": ["colreg", "collision"],
        "STCW": ["stcw"],
        "MLC": ["mlc"]
    }

    text_lower = text.lower()

    for law, keywords in laws.items():
        if any(k in text_lower for k in keywords):
            return law

    return "UNKNOWN"

# ============================
# SPLIT ARTICLES
# ============================
def split_articles(text):

    pattern = r"(MADDE\s+\d+|Madde\s+\d+|Rule\s+\d+|ARTICLE\s+\d+|Article\s+\d+)"

    parts = re.split(pattern, text)

    articles = []

    for i in range(1, len(parts), 2):
        title = parts[i]
        body = parts[i+1] if i+1 < len(parts) else ""

        full = f"{title} {body}".strip()

        if len(full.split()) > 30:
            articles.append((title.strip(), full))

    return articles

# ============================
# KEYWORD EXTRACTION (SIMPLE)
# ============================
def extract_keywords(text):

    words = text.lower().split()

    important = [w for w in words if len(w) > 6]

    return list(set(important[:10]))

# ============================
# MAIN
# ============================
def process():

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    structured = []

    for item in data:

        text = item["text"]

        law = detect_law(text)

        articles = split_articles(text)

        if not articles:
            structured.append({
                "law": law,
                "article": "UNKNOWN",
                "title": "",
                "text": text,
                "keywords": extract_keywords(text)
            })
        else:
            for title, full_text in articles:

                structured.append({
                    "law": law,
                    "article": title,
                    "title": title,
                    "text": full_text,
                    "keywords": extract_keywords(full_text)
                })

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(structured, f, ensure_ascii=False, indent=2)

    print(f"✔ Structured dataset saved: {len(structured)} entries")


if __name__ == "__main__":
    process()