import streamlit as st
import os
from pypdf import PdfReader
import requests
import json

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
def find_relevant_chunks(prompt, chunks, top_n=6):
    prompt_words = prompt.lower().split()
    scored_chunks = []
    for item in chunks:
        chunk_text = item["text"]
        score = sum(1 for word in prompt_words if word in chunk_text.lower())
        scored_chunks.append((score, item))
    
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
            # Sla per chunk ook de bestandsnaam op als bron
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
                    "model": "llama-3.3-70b-versatile",
                    "messages": [
                        {"role": "system", "content": Jij bent een zeer nauwkeurige hypotheekadviseur. Analyseer de betekenis van de vraag en de context. Let op: 'consumptief lenen' of 'niet-aftrekbare rente' / 'fiscaal niet aftrekbaar' zijn in deze gidsen vaak aan elkaar gekoppeld. Als de tekst spreekt over financieringslastpercentages bij een lening waarvan de rente niet fiscaal aftrekbaar is, betekent dit dat consumptief/niet-aftrekbaar lenen wel degelijk mogelijk is. Vermeld onder je antwoord altijd de bron (bestandsnaam). Verzin nooit dingen die er niet staan en ga niet speculeren over de focus van een geldverstrekker."},
                        {"role": "user", "content": f"Context:\n{relevant_context}\n\nVraag: {prompt}"}
                    ]
                }
                headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
                response = requests.post(url, headers=headers, data=json.dumps(payload))
                answer = response.json()["choices"][0]["message"]["content"]
            except Exception as e:
                answer = f"Fout: {e}"
            st.markdown(answer)
            st.session_state.messages.append({"role": "assistant", "content": answer})
