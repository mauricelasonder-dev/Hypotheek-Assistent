import streamlit as st
import os
from pypdf import PdfReader
import requests
import json
from sentence_transformers import SentenceTransformer
import numpy as np

# Laad een snel en slim lokaal embedding model (gebeurt eenmalig bij opstarten)
@st.cache_resource
def load_model():
    return SentenceTransformer('all-MiniLM-L6-v2')

embed_model = load_model()

st.set_page_config(page_title="Hypotheek Acceptatie Assistent", page_icon="🏠")
st.title("🏠 Acceptatiebeleid Assistent")

PASSWORD = "jouw-wachtwoord-hier"

# Functie om PDF te lezen en slim op te knippen met overlap
# Verhoog de chunk_size voor meer context en de overlap voor betere aansluiting
def get_pdf_chunks(pdf_file, chunk_size=2000, chunk_overlap=400):
    reader = PdfReader(pdf_file)
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

# Zoek alleen de meest relevante stukjes voor de vraag
def find_relevant_chunks(prompt, chunks, top_n=4):
    prompt_vector = embed_model.encode(prompt)
    
    scored_chunks = []
    for item in chunks:
        # Bereken de overeenkomst op basis van de vectoren
        similarity = np.dot(prompt_vector, item["embedding"]) / (
            np.linalg.norm(prompt_vector) * np.linalg.norm(item["embedding"])
        )
        scored_chunks.append((similarity, item))
    
    scored_chunks.sort(key=lambda x: x[0], reverse=True)
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
# Haal alle PDF's op, inclusief de bestandsnaam voor de bronvermelding
pdf_chunks = []
for file in os.listdir("."):
    if file.endswith(".pdf"):
        with open(file, "rb") as f:
            chunks = get_pdf_chunks(f)
            # Sla per chunk de tekst, bron én direct de vector-embedding op
            for chunk in chunks:
                vector = embed_model.encode(chunk)
                pdf_chunks.append({"text": chunk, "source": file, "embedding": vector})

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
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {
                    "role": "system", 
                    "content": "Jij bent een nauwkeurige hypotheekadviseur. Analyseer de betekenis van de vraag en de context. Let op: begrippen als 'consumptief lenen' kunnen in de tekst beschreven zijn als 'lening waarvan de rente niet fiscaal aftrekbaar is'. Als dit zo is, is het dus wel mogelijk. Vermeld altijd de bron. Ga niet speculeren."
                },
                {
                    "role": "user", 
                    "content": f"Context:\n{relevant_context}\n\nVraag: {prompt}"
                }
            ]
        }
                headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
                response = requests.post(url, headers=headers, data=json.dumps(payload))
                answer = response.json()["choices"][0]["message"]["content"]
            except Exception as e:
                answer = f"Fout: {e}"
            st.markdown(answer)
            st.session_state.messages.append({"role": "assistant", "content": answer})
