import streamlit as st
import os
from pypdf import PdfReader
import requests
import json

st.set_page_config(page_title="Hypotheek Acceptatie Assistent", page_icon="🏠")
st.title("🏠 Acceptatiebeleid Assistent")

PASSWORD = "jouw-wachtwoord-hier"

# Functie om PDF te lezen en op te knippen (gecached voor snelheid)
@st.cache_data
def get_pdf_chunks_cached(file_path, chunk_size=2000, chunk_overlap=400):
    reader = PdfReader(file_path)
    full_text = ""
    for page in reader.pages:
        text = page.extract_text()
        if text:
            full_text += text + "\n"
            
    chunks = []
    start = 0
    while start < len(full_text):
        end = start + chunk_size
        chunk = full_text[start:end]
        chunks.append(chunk)
        start += chunk_size - chunk_overlap
        
    return chunks

# Supersnelle trefwoorden-zoekfunctie met synoniemen
def find_relevant_chunks(prompt, chunks, top_n=6):
    prompt_lower = prompt.lower()
    
    # Breid de zoektermen automatisch uit bij specifieke begrippen
    search_words = prompt_lower.split()
    if "consumptief" in prompt_lower or "lening" in prompt_lower:
        search_words.extend(["niet", "fiscaal", "aftrekbaar", "rente", "financieringslastpercentages"])
    
    scored_chunks = []
    for item in chunks:
        chunk_text = item["text"].lower()
        score = sum(1 for word in search_words if word in chunk_text)
        if score > 0:
            scored_chunks.append((score, item))
    
    scored_chunks.sort(key=lambda x: x[0], reverse=True)
    
    if not scored_chunks:
        return chunks[:top_n]
        
    return [item[1] for item in scored_chunks[:top_n]]

# Wachtwoord logic...
if "password_correct" not in st.session_state: st.session_state.password_correct = False
if not st.session_state.password_correct:
    pwd = st.text_input("Wachtwoord:", type="password")
    if st.button("Inloggen") and pwd == PASSWORD:
        st.session_state.password_correct = True
        st.rerun()
    st.stop()

api_key = st.secrets.get("GROQ_API_KEY") or st.secrets.get("GEMINI_API_KEY")

# Laad alle PDF's bliksemsnel in via de cache
pdf_chunks = []
for file in os.listdir("."):
    if file.endswith(".pdf"):
        chunks = get_pdf_chunks_cached(file)
        for chunk in chunks:
            pdf_chunks.append({"text": chunk, "source": file})

if "messages" not in st.session_state: st.session_state.messages = []
for message in st.session_state.messages:
    with st.chat_message(message["role"]): st.markdown(message["content"])

if prompt := st.chat_input("Stel je vraag over het acceptatiebeleid..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Zoeken in je documentatie..."):
            relevant_items = find_relevant_chunks(prompt, pdf_chunks, top_n=6)
            
            context_texts = []
            for item in relevant_items:
                context_texts.append(f"Bron: {item['source']}\nInhoud: {item['text']}")
            
            relevant_context = "\n\n---\n\n".join(context_texts)
            
            try:
                url = "https://api.groq.com/openai/v1/chat/completions"
                payload = {
                   "model": "llama-3.1-8b-instant",
                    "messages": [
                        {
                            "role": "system", 
                            "content": (
                                "Jij bent een specialistische Hypotheek Acceptatie Assistent. "
                                "Geef antwoord met een korte inleiding van max 2 zinnen, gevolgd door exact één tabel met deze kolommen:\n"
                                "| Geldverstrekker | Beleid (Kort & Bondig) | Letterlijke omschrijving uit gids | Bronvermelding |\n"
                                "Speculeer nooit, verwerk synoniemen (zoals consumptief lenen = niet-aftrekbare rente) en vermeld altijd de bron."
                            )
                        },
                        {
                            "role": "user", 
                            "content": f"Context:\n{relevant_context}\n\nVraag: {prompt}"
                        }
                    ]
                }
                headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
                response = requests.post(url, headers=headers, data=json.dumps(payload))
                
                res_json = response.json()
                if "choices" in res_json:
                    answer = res_json["choices"][0]["message"]["content"]
                else:
                    answer = f"Groq API melding: {res_json}"
                    
            except Exception as e:
                answer = f"Fout bij verwerken: {e}"
                
            st.markdown(answer)
            st.session_state.messages.append({"role": "assistant", "content": answer})
