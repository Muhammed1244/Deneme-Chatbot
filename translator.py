import torch
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

model = None
tokenizer = None
_model_loaded = False

def load_model():
    global model, tokenizer, _model_loaded

    if _model_loaded:
        return

    model_name = "facebook/nllb-200-distilled-600M"

    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSeq2SeqLM.from_pretrained(model_name)

    model.to("cuda" if torch.cuda.is_available() else "cpu")

    _model_loaded = True

import re

def is_english(text: str) -> bool:
    text = text.lower()

    words = re.findall(r"[a-zA-Z]+", text)

    if len(words) < 3:
        return False

    english_words = {
        "the", "and", "is", "are", "legal",
        "court", "law", "document", "case"
    }

    hits = sum(w in english_words for w in words)

    return hits / len(words) > 0.3


def translate_to_turkish(text: str) -> str:
    load_model()

    tokenizer.src_lang = "eng_Latn"

    device = "cuda" if torch.cuda.is_available() else "cpu"

    encoded = tokenizer(text, return_tensors="pt", truncation=True)
    encoded = {k: v.to(device) for k, v in encoded.items()}

    forced_id = tokenizer.lang_code_to_id["tur_Latn"]

    with torch.no_grad():
        generated_tokens = model.generate(
            **encoded,
            forced_bos_token_id=forced_id,
            max_new_tokens=128
        )

    return tokenizer.batch_decode(generated_tokens, skip_special_tokens=True)[0]



def smart_translate(text: str) -> str:
    if not is_english(text):
        return text

    return translate_to_turkish(text)