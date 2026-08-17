import streamlit as st
import os
from pypdf import PdfReader
import google.generativeai as genai

st.set_page_config(page_title="Hypotheek Acceptatie Assistent", page_icon="🏠")
st.title("🏠 Acceptatiebeleid Assistent")

PASSWORD = "jouw-wachtwoord-hier"

# Functie voor PDF verwerking
@st.cache_data
def get_pdf_chunks_cached(file_path, chunk_size=2000, chunk_overlap=400):
    reader = PdfReader(file_path)
    full_text = "\n".join([page.extract_text() for page in reader.pages if page.extract_text()])
    return [full_text[i:i+chunk_size] for i in range(0, len(full_text), chunk_size - chunk_overlap)]

# Zoekfunctie
def find_relevant_chunks(prompt, chunks, top_n=6):
    search_words = prompt.lower().split()
    scored_chunks = []
    for item in chunks:
        score = sum(1 for word in search_words if word in item["text"].lower())
        if score > 0: scored_chunks.append((score, item))
    scored_chunks.sort(key=lambda x: x[0], reverse=True)
    return [item[1] for item in scored_chunks[:top_n]] if scored_chunks else chunks[:top_n]

# Auth logic
if "password_correct" not in st.session_state: st.session_state.password_correct = False
if not st.session_state.password_correct:
    pwd = st.text_input("Wachtwoord:", type="password")
    if st.button("Inloggen") and pwd == PASSWORD:
        st.session_state.password_correct = True
        st.rerun()
    st.stop()

# Gemini configuratie
api_key = st.secrets.get("GEMINI_API_KEY")
genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-2.5-flash')

# PDF loading
pdf_chunks = []
for file in os.listdir("."):
    if file.endswith(".pdf"):
        for chunk in get_pdf_chunks_cached(file):
            pdf_chunks.append({"text": chunk, "source": file})

if "messages" not in st.session_state: st.session_state.messages = []
for message in st.session_state.messages:
    with st.chat_message(message["role"]): st.markdown(message["content"])

if prompt := st.chat_input("Stel je vraag over het acceptatiebeleid..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Zoeken in je documentatie..."):
            relevant_items = find_relevant_chunks(prompt, pdf_chunks)
            context = "\n\n---\n\n".join([f"Bron: {item['source']}\nInhoud: {item['text']}" for item in relevant_items])
            
            system_instruction = (
                "Jij bent een specialistische Hypotheek Acceptatie Assistent. "
                "Geef antwoord met een korte inleiding, gevolgd door een tabel met: "
                "| Geldverstrekker | Beleid (Kort & Bondig) | Letterlijke omschrijving | Bron |"
            )
            
            try:
                response = model.generate_content(f"{system_instruction}\n\nContext:\n{context}\n\nVraag: {prompt}")
                answer = response.text
            except Exception as e:
                answer = f"Er ging iets mis met de verbinding naar Gemini: {e}"
                
            st.markdown(answer)
            st.session_state.messages.append({"role": "assistant", "content": answer})
