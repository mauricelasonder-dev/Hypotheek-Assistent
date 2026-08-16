import streamlit as st
import os
from pypdf import PdfReader
import requests
import json

st.set_page_config(page_title="Hypotheek Acceptatie Assistent", page_icon="🏠")
st.title("🏠 Acceptatiebeleid Assistent")

PASSWORD = "jouw-wachtwoord-hier"

# Sla alle tekst op in kleine, behapbare stukjes (chunks)
@st.cache_data
def get_pdf_chunks():
    chunks = []
    chunk_size = 1500 # Tekens per stukje
    for file in os.listdir("."):
        if file.endswith(".pdf"):
            reader = PdfReader(file)
            full_text = ""
            for page in reader.pages:
                text = page.extract_text()
                if text: full_text += text
            # Knip in stukjes
            for i in range(0, len(full_text), chunk_size):
                chunks.append(full_text[i:i+chunk_size])
    return chunks

# Zoek alleen de meest relevante stukjes voor de vraag
def find_relevant_chunks(prompt, chunks, top_n=3):
    # Simpele zoekopdracht: kijkt welk stukje de meeste trefwoorden bevat
    prompt_words = prompt.lower().split()
    scored_chunks = []
    for chunk in chunks:
        score = sum(1 for word in prompt_words if word in chunk.lower())
        scored_chunks.append((score, chunk))
    # Sorteer op relevantie
    scored_chunks.sort(key=lambda x: x[0], reverse=True)
    return [chunk for score, chunk in scored_chunks[:top_n]]

# Wachtwoord logic...
if "password_correct" not in st.session_state: st.session_state.password_correct = False
if not st.session_state.password_correct:
    pwd = st.text_input("Wachtwoord:", type="password")
    if st.button("Inloggen") and pwd == PASSWORD:
        st.session_state.password_correct = True
        st.rerun()
    st.stop()

api_key = st.secrets.get("GROQ_API_KEY") or st.secrets.get("GEMINI_API_KEY")
pdf_chunks = get_pdf_chunks()

if "messages" not in st.session_state: st.session_state.messages = []
for message in st.session_state.messages:
    with st.chat_message(message["role"]): st.markdown(message["content"])

if prompt := st.chat_input("Stel je vraag over het acceptatiebeleid..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Zoeken in je documentatie..."):
            relevant_context = "\n\n".join(find_relevant_chunks(prompt, pdf_chunks))
            
            try:
                url = "https://api.groq.com/openai/v1/chat/completions"
                payload = {
                    "model": "llama-3.3-70b-versatile",
                    "messages": [
                        {"role": "system", "content": f"Je bent een assistent. Beantwoord de vraag op basis van deze fragmenten:\n\n{relevant_context}"},
                        {"role": "user", "content": prompt}
                    ]
                }
                headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
                response = requests.post(url, headers=headers, data=json.dumps(payload))
                answer = response.json()["choices"][0]["message"]["content"]
            except Exception as e:
                answer = f"Fout: {e}"
            st.markdown(answer)
            st.session_state.messages.append({"role": "assistant", "content": answer})
