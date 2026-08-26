# app.py 
# MUST BE AT THE VERY TOP
# app.py (Replace lines 1-3 at the top)
import nest_asyncio

try:
    nest_asyncio.apply()
except Exception as e:
    print(f"Skipping nest_asyncio: {e}")

import streamlit as st
from pathlib import Path
from streamlit_mic_recorder import mic_recorder
from faster_whisper import WhisperModel
from rag_core import ask

# =====================================================
# PAGE CONFIG
# =====================================================

st.set_page_config(
    page_title="Denizcilik Mevzuatı Asistanı", 
    page_icon="⚖️", 
    layout="centered"
)
st.title("⚖️ UAB Denizcilik Mevzuatı Chatbot")

# =====================================================
# WHISPER MODEL (LAZY LOAD)
# =====================================================

@st.cache_resource
def load_whisper():
    """Lazy loads Whisper model to prevent VRAM / thread locking at boot."""
    return WhisperModel("base", device="cpu", compute_type="int8")

# =====================================================
# RETRIEVER INITIALIZATION
# =====================================================

@st.cache_resource
def init_retriever():
    """Loads the fast ChromaDB + BGE-M3 retriever."""
    try:
        from retrieval import HybridRetriever
        return HybridRetriever(load=True)
    except Exception as e:
        st.error(f"Retriever yüklenirken hata oluştu: {e}")
        return None

retriever = init_retriever()

# =====================================================
# SESSION STATE INITIALIZATION
# =====================================================

if "messages" not in st.session_state:
    st.session_state.messages = []

# =====================================================
# RENDER CHAT HISTORY & CITATIONS
# =====================================================

for i, msg in enumerate(st.session_state.messages):
    with st.chat_message(msg["role"]):
        st.write(msg["content"])
        
        # Render citations panel if present on assistant messages
        citations = msg.get("citations")
        if msg["role"] == "assistant" and citations is not None:
            # Expand only the last message's citations by default
            is_last_message = (i == len(st.session_state.messages) - 1)
            
            with st.expander("📚 Kaynaklar ve Referanslar", expanded=is_last_message):
                if not citations:
                    st.info("Bu yanıt için doğrudan kaynak atıfı bulunmamaktadır.")

                for j, meta in enumerate(citations):
                    pdf_file = meta.get("source_file", "Genel_Kaynak.pdf")
                    
                    # Handles both single page numbers and page ranges
                    page_start = meta.get("page_start", meta.get("page", "?"))
                    page_end = meta.get("page_end", page_start)
                    page_text = f"{page_start}" if str(page_start) == str(page_end) else f"{page_start}-{page_end}"

                    st.markdown(f"**Dosya:** `{pdf_file}` | **Sayfa:** `{page_text}`")

                    # Check local 'Belgeler' folder for download link
                    pdf_path = Path("Belgeler") / pdf_file
                    if pdf_path.exists():
                        with open(pdf_path, "rb") as f:
                            pdf_bytes = f.read()

                        col1, col2 = st.columns(2)
                        with col1:
                            st.download_button(
                                label="⬇️ PDF İndir",
                                data=pdf_bytes,
                                file_name=pdf_file,
                                mime="application/pdf",
                                key=f"download_{i}_{j}"
                            )
                        with col2:
                            st.download_button(
                                label="👁️ Görüntüle",
                                data=pdf_bytes,
                                file_name=pdf_file,
                                mime="application/pdf",
                                key=f"view_{i}_{j}"
                            )
                    else:
                        if not pdf_file.endswith(".pdf"):
                            st.caption("🌐 Canlı İnternet Arama Kaynağı")
                        else:
                            st.caption(f"📁 Belge yerel dizinde taranmış fakat '{pdf_file}' bulunamadı.")

# =====================================================
# 🎤 VOICE INPUT
# =====================================================

st.subheader("🎤 Ses ile Sor")

audio = mic_recorder(
    start_prompt="🎙️ Kayda başla",
    stop_prompt="⏹️ Durdur",
    just_once=True,
    use_container_width=True,
    format="wav"
)

voice_text = None

if audio:
    st.info("Ses analiz ediliyor...")
    whisper_model = load_whisper()

    audio_path = "temp.wav"
    with open(audio_path, "wb") as f:
        f.write(audio["bytes"])

    segments, info = whisper_model.transcribe(audio_path)
    voice_text = " ".join([s.text for s in segments])

    st.success(f"Algılanan: {voice_text}")

# =====================================================
# TEXT INPUT & QUERY HANDLER
# =====================================================

user_input = st.chat_input("Mevzuat veya genel bilginizi yazın...")
final_input = voice_text if voice_text else user_input

if final_input:
    # 1. Save user message
    st.session_state.messages.append({
        "role": "user",
        "content": final_input
    })

    # 2. Query processing
    if retriever is None:
        st.error("RAG Veritabanı yüklenemedi. Lütfen 'build_index_fast.py' dosyasını çalıştırdığınızdan emin olun.")
    else:
        with st.spinner("⚖️ Yerel mevzuat ve internet kaynakları taranıyor..."):
            result = ask(retriever, final_input)

        # 3. Save assistant message and citations directly to history
        st.session_state.messages.append({
            "role": "assistant",
            "content": result["answer"],
            "citations": result["citations"]
        })
        
        # Force re-run to immediately render the new messages in the history loop
        st.rerun()
