# rag_core.py
import urllib.parse
import requests
from bs4 import BeautifulSoup
from llm import generate  # Import your Groq generator function

# Optional import if citation_engine.py is present in project
try:
    from citation_engine import build_citations
except ImportError:
    build_citations = None


def web_search(query: str, max_results: int = 3) -> str:
    """
    Scans the internet using DuckDuckGo Lite / Wikipedia fallback.
    """
    print(f"🌐 [WEB] İnternet taranıyor: '{query}'...")
    try:
        encoded_query = urllib.parse.quote_plus(query)
        url = "https://lite.duckduckgo.com/lite/"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        data = f"q={encoded_query}"

        response = requests.post(url, headers=headers, data=data, timeout=8)
        if response.status_code == 200 and "captcha" not in response.text.lower():
            soup = BeautifulSoup(response.text, "html.parser")
            links = soup.select("td.result-link a")
            snippets = soup.select("td.result-snippet")

            context_blocks = []
            for i, (link_tag, snippet_tag) in enumerate(zip(links, snippets)):
                if i >= max_results:
                    break

                title = link_tag.get_text(strip=True)
                href = link_tag.get("href", "")
                snippet = snippet_tag.get_text(strip=True) if snippet_tag else ""

                if "uddg=" in href:
                    parsed_href = urllib.parse.parse_qs(
                        urllib.parse.urlparse(href).query
                    )
                    href = parsed_href.get("uddg", [href])[0]

                context_blocks.append(
                    f"--- [İnternet Kaynağı {i+1}: {href}] ---\n"
                    f"Başlık: {title}\n"
                    f"Özet: {snippet}\n"
                )

            if context_blocks:
                return "\n".join(context_blocks)

    except Exception as e:
        print(f"⚠️ [WEB] Arama hatası: {e}")

    return ""


def ask(retriever, query: str) -> dict:
    if not retriever or not hasattr(retriever, "query_engine") or not retriever.query_engine:
        return {
            "answer": "Hata: RAG dikey veritabanı yüklenemedi.",
            "citations": [],
            "is_web_search": False,
        }

    try:
        print(f"\n🔍 [LOCAL] ChromaDB sorgulanıyor: '{query}'")

        # Query ChromaDB nodes
        nodes = retriever.query_engine.retrieve(query)

        context_chunks = []
        raw_chunks = []
        citations = []
        seen_citations = set()
        highest_score = 0.0

        for source_node in nodes:
            score = getattr(source_node, "score", 0.0) or 0.0
            if score > highest_score:
                highest_score = score

            metadata = getattr(source_node.node, "metadata", {})
            file_name = metadata.get("source_file", "Bilinmeyen_Dosya.pdf")
            
            # Read page_start and page_end directly from metadata (fallback to 'page')
            page_start = metadata.get("page_start", metadata.get("page", 1))
            page_end = metadata.get("page_end", page_start)
            
            text_content = source_node.node.get_content()

            # Format text block for LLM prompt context
            page_range_str = f"{page_start}" if str(page_start) == str(page_end) else f"{page_start}-{page_end}"
            context_chunks.append(
                f"--- [YEREL MEVZUAT KAYNAK: {file_name}, SAYFA: {page_range_str}] ---\n{text_content}\n"
            )

            # Store structured data block
            chunk_data = {
                "source_file": file_name,
                "page_start": page_start,
                "page_end": page_end,
                "text": text_content,
            }
            raw_chunks.append(chunk_data)

            # Build inline citation dictionary
            cit_key = (file_name, page_start, page_end)
            if cit_key not in seen_citations:
                seen_citations.add(cit_key)
                citations.append({
                    "source_file": file_name,
                    "page_start": page_start,
                    "page_end": page_end,
                })

        print(f"📊 [ROUTER] En yüksek benzerlik skoru: {highest_score:.4f}")

        # Use external build_citations function if available
        if build_citations and raw_chunks:
            citations = build_citations(raw_chunks)

        # Fallback to web search if similarity score is too low or context is empty
        is_web_search = False
        if highest_score < 0.30 or not context_chunks:
            print("🔀 [ROUTER] Skor düşük, internet araması başlatılıyor...")
            web_context = web_search(query)

            if web_context:
                is_web_search = True
                context_str = "=== İNTERNET ARAMA BULGULARI ===\n" + web_context
                citations.append({
                    "source_file": "İnternet_Arama_Sonuçları.pdf",
                    "page_start": "Canlı",
                    "page_end": "Arama",
                })
            else:
                context_str = (
                    "\n".join(context_chunks)
                    if context_chunks
                    else "Hiçbir kaynak bulunamadı."
                )
        else:
            context_str = "\n".join(context_chunks)

        groq_prompt = (
            f"Aşağıdaki kaynak belgeler doğrultusunda soruyu yanıtla.\n"
            f"Cevabını oluştururken yalnızca bu bilgilere bağlı kal. Bilgi dışına çıkma.\n\n"
            f"---------------------\n"
            f"{context_str}\n"
            f"---------------------\n\n"
            f"Soru: {query}"
        )

        print(f"🚀 [LLM] Prompt Groq'a gönderiliyor...")
        answer = generate(groq_prompt)

        return {
            "answer": answer,
            "citations": citations,
            "is_web_search": is_web_search,
        }

    except Exception as e:
        print(f"❌ [SYSTEM] ask() fonksiyonunda hata: {e}")
        return {
            "answer": f"Bir hata oluştu:\n\n{e}",
            "citations": [],
            "is_web_search": False,
        }