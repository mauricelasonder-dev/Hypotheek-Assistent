import streamlit as st
import os
from pypdf import PdfReader
import google.generativeai as genai

st.set_page_config(page_title="Hypotheek Acceptatie Assistent", page_icon="🏠")
st.title("🏠 Acceptatiebeleid Assistent")

PASSWORD = "jouw-wachtwoord-hier"

# 1. Supersnelle PDF-inlezer die alle bestanden globaal cached in het geheugen
@st.cache_resource
def load_all_pdfs():
    all_chunks = []
    chunk_size = 2000
    chunk_overlap = 400
    
    for file in os.listdir("."):
        if file.endswith(".pdf"):
            try:
                reader = PdfReader(file)
                full_text = ""
                for page in reader.pages:
                    text = page.extract_text()
                    if text:
                        full_text += text + "\n"
                
                # Opsplitsen in chunks
                start = 0
                while start < len(full_text):
                    end = start + chunk_size
                    chunk = full_text[start:end]
                    all_chunks.append({"text": chunk, "source": file})
                    start += chunk_size - chunk_overlap
            except Exception as e:
                print(f"Fout bij lezen {file}: {e}")
                
    return all_chunks

# Wachtwoord logic
if "password_correct" not in st.session_state: st.session_state.password_correct = False
if not st.session_state.password_correct:
    pwd = st.text_input("Wachtwoord:", type="password")
    if st.button("Inloggen") and pwd == PASSWORD:
        st.session_state.password_correct = True
        st.rerun()
    st.stop()

# API configuratie
api_key = st.secrets.get("GEMINI_API_KEY")
genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-3.6-flash')

# Laad alle PDF's eenmalig in het geheugen (supersnel!)
pdf_chunks = load_all_pdfs()

if "messages" not in st.session_state: st.session_state.messages = []
for message in st.session_state.messages:
    with st.chat_message(message["role"]): st.markdown(message["content"])

if prompt := st.chat_input("Stel je vraag over het acceptatiebeleid..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Zoeken in je gidsen..."):
            prompt_lower = prompt.lower()
            
            # Slimme trefwoorden-zoektocht over ALLE geladen PDF's heen
            search_words = prompt_lower.split()
            scored = []
            for item in pdf_chunks:
                # Geef extra gewicht als de geldverstrekker of zoekterm direct in de tekst of bron staat
                score = sum(2 if w in item["text"].lower() or w in item["source"].lower() else 0 for w in search_words)
                # Tel ook gewone overeenlagen mee
                score += sum(1 for w in search_words if w in item["text"].lower())
                if score > 0:
                    scored.append((score, item))
            
            scored.sort(key=lambda x: x[0], reverse=True)
            
            # Neem de top relevante stukken mee als context
            matched_chunks = [item[1] for item in scored[:6]] if scored else pdf_chunks[:6]

            context = "\n\n---\n\n".join([f"Bron: {item['source']}\nInhoud: {item['text']}" for item in matched_chunks])
            
            system_instruction = (
                "Jij bent een specialistische Hypotheek Acceptatie Assistent. "
                "Geef antwoord met een korte inleiding, gevolgd door een tabel met: "
                "| Geldverstrekker | Beleid (Kort & Bondig) | Letterlijke omschrijving | Bron |\n"
                "Zoek goed in de aangeleverde context naar de gevraagde geldverstrekker (bijv. NIBC). "
                "Als de informatie in de context staat, neem deze dan direct op in de tabel. Verzin nooit gegevens."
            )
            
            try:
                response = model.generate_content(f"{system_instruction}\n\nContext:\n{context}\n\nVraag: {prompt}")
                answer = response.text
            except Exception as e:
                answer = f"Er ging iets mis met de verbinding naar Gemini: {e}"
                
            st.markdown(answer)
            st.session_state.messages.append({"role": "assistant", "content": answer})
