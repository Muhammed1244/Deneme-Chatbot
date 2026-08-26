# retrieval.py
import os
import nltk

# Streamlit Cloud üzerinde NLTK hardlink / pathsec hatasını engellemek için
os.environ["NLTK_DATA"] = "/tmp/nltk_data"
nltk.download("stopwords", download_dir="/tmp/nltk_data", quiet=True)
from pathlib import Path
import chromadb
from llama_index.core import VectorStoreIndex, Settings
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.core.llms import MockLLM

class HybridRetriever:
    def __init__(self, load=True):
        BASE_DIR = Path(__file__).resolve().parent
        CHROMA_DB_DIR = BASE_DIR / "chroma_db"
        DATASET_PATH = BASE_DIR / "clean_data" / "dataset_structured.json"
        
        # 1. Configure Embeddings
        Settings.embed_model = HuggingFaceEmbedding(
            model_name="BAAI/bge-m3",
            max_length=8192,
            device="cpu"
        )
        Settings.llm = MockLLM()
        
        # 2. If ChromaDB doesn't exist (e.g. fresh deployment), build it!
        if not CHROMA_DB_DIR.exists() or not any(CHROMA_DB_DIR.iterdir()):
            print("⚡ ChromaDB not found on server. Building index automatically...")
            from build_index_fast import build_index
            build_index()

        # 3. Connect to ChromaDB
        db = chromadb.PersistentClient(path=str(CHROMA_DB_DIR))
        chroma_collection = db.get_collection("denizcilik_mevzuati")
        vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
        
        index = VectorStoreIndex.from_vector_store(vector_store=vector_store)
        self.query_engine = index.as_retriever(similarity_top_k=5)
