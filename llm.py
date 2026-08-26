# llm.py

import os
from groq import Groq

# ==========================================================
# CLIENT
# ==========================================================

client = Groq(
    api_key=os.getenv("GROQ_API_KEY")
)

MODEL = "openai/gpt-oss-120b"

# ==========================================================
# SYSTEM PROMPT
# ==========================================================

SYSTEM_PROMPT = """
Sen uzman bir denizcilik hukuku ve denizcilik mevzuatı asistanısın.


KESİNLİKLE UYULACAK KURALLAR

1. Kaynaklarda bulunmayan bilgi üretme.

2. Tahmin yapma.

3. Kanun uydurma.

4. Madde numarası uydurma.

5. Emin değilsen bunu açıkça söyle.

6. Türkçe dışında cevap verme.

7. Gereksiz tekrar yapma.

8. Cevabı mümkün olduğunca düzenli yaz.

Cevap formatı:

## Kısa Cevap

Birkaç cümlede açıkla.

## Açıklama

Konuyu maddeler halinde ayrıntılı açıkla.

• ...

• ...

• ...

## Kaynakça

Kullanılan kaynakların hepsini belirt.

Her kaynak için şu formatı kullan:

- source_file, sayfa: page_start - page_end 
- source_file, sayfa: page_start - page_end ...

Kaynaklarda cevap bulunmuyorsa şu ifadeyi kullan:

"Sağlanan kaynaklarda bu soruya doğrudan cevap bulunamamaktadır."

Asla bu ifadeyi değiştirme.
"""

# ==========================================================
# GENERATE
# ==========================================================

def generate(prompt):

    response = client.chat.completions.create(

        model=MODEL,

        temperature=0,

        max_tokens=1200,

        top_p=0.9,

        messages=[
            {
                "role": "system",
                "content": SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    return response.choices[0].message.content