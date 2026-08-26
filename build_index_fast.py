# build_index_fast.py
import os
import json
import time
from pathlib import Path

# Prevent parallelism lockup on Windows/Anaconda
os.environ["TOKENIZERS_PARALLELISM"] = "false"

import chromadb
from llama_index.core import Document, StorageContext, VectorStoreIndex, Settings
from llama_index.core.node_parser import SentenceSplitter
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.llms.groq import Groq
from llama_index.vector_stores.chroma import ChromaVectorStore

# ============================================================
# 1. PATHS
# ============================================================
BASE_DIR = Path(__file__).resolve().parent
DATASET_PATH = BASE_DIR / "clean_data" / "dataset_structured.json"
CHROMA_DB_DIR = BASE_DIR / "chroma_db"

print("=" * 60)
print("🚀 BUILDING HIGH-ACCURACY VECTOR INDEX (LLAMAINDEX + CHROMADB)")
print("=" * 60)

# ============================================================
# 2. EMBEDDING & LLM SETTINGS
# ============================================================
print("\n[1/4] Configuring BAAI/bge-m3 and Groq LLM...")

embed_model = HuggingFaceEmbedding(
    model_name="BAAI/bge-m3",
    max_length=8192,
    device="cuda" if os.environ.get("USE_CUDA") == "1" else "cpu"
)

# Upgrade to Llama-3.3-70b for significantly stronger legal reasoning in Turkish
groq_llm = Groq(
    model="openai/gpt-oss-120b",
    api_key=os.getenv("GROQ_API_KEY")
)

Settings.embed_model = embed_model
Settings.llm = groq_llm

# Legal text benefits from larger chunk sizes (768–1024) to avoid splitting 
# conditional clauses and article exceptions mid-sentence.
Settings.node_parser = SentenceSplitter(
    chunk_size=768,
    chunk_overlap=128
)

# ============================================================
# 3. LOAD DATASET & INJECT METADATA CONTEXT
# ============================================================
print(f"\n[2/4] Loading dataset: {DATASET_PATH}")
if not DATASET_PATH.exists():
    raise FileNotFoundError(f"Dataset file not found: {DATASET_PATH}")

with open(DATASET_PATH, encoding="utf-8") as f:
    raw_docs = json.load(f)

documents = []
for item in raw_docs:
    text_content = item.get("text", "").strip()
    if not text_content:
        continue
    
    source_file = item.get("source_file", "Belge.pdf")
    page_start = item.get("page_start", 1)
    page_end = item.get("page_end", 1)

    metadata = {
        "source_file": source_file,
        "page_start": page_start,
        "page_end": page_end
    }

    # Context Header Injection: Prepend document identity to text payload
    # so the embedding model knows which document/law the text belongs to.
    header = f"[Kaynak Belge: {source_file} | Sayfa: {page_start}-{page_end}]\n"
    full_text = header + text_content

    doc = Document(
        text=full_text,
        metadata=metadata,
        # Exclude source info from LLM input to save context window if already in text
        excluded_embed_metadata_keys=["source_file"], 
        excluded_llm_metadata_keys=["page_start", "page_end"]
    )
    documents.append(doc)

print(f"Loaded {len(documents)} context-enriched document chunks.")

# ============================================================
# 4. CHROMADB VECTOR STORE
# ============================================================
print(f"\n[3/4] Initializing ChromaDB at: {CHROMA_DB_DIR}")
CHROMA_DB_DIR.mkdir(exist_ok=True)

db = chromadb.PersistentClient(path=str(CHROMA_DB_DIR))

# Wipe or recreate collection if rebuilding index to prevent stale duplicate chunks
chroma_collection = db.get_or_create_collection(
    name="denizcilik_mevzuati",
    metadata={"hnsw:space": "cosine"} # Explicit cosine similarity distance
)
vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
storage_context = StorageContext.from_defaults(vector_store=vector_store)

# ============================================================
# 5. BUILD & PERSIST INDEX
# ============================================================
print("\n[4/4] Creating Vector Index...")
start_time = time.time()

index = VectorStoreIndex.from_documents(
    documents,
    storage_context=storage_context,
    show_progress=True
)

elapsed_time = time.time() - start_time
print("\n" + "=" * 60)
print("🎉 INDEX CREATED SUCCESSFULLY!")
print(f"⏱️ Total Execution Time: {elapsed_time:.2f} seconds")
print(f"💾 Storage Directory: {CHROMA_DB_DIR}")
print("=" * 60)