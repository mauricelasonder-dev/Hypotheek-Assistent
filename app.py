import streamlit as st
import os
from pypdf import PdfReader
import google.generativeai as genai

# Pagina instellingen
st.set_page_config(page_title="Hypotheek Acceptatie Assistent", page_icon="🏠")

st.title("🏠 Acceptatiebeleid Assistent")

# Wachtwoord beveiliging
PASSWORD = "jouw-wachtwoord-hier" # Pas aan naar wens

def check_password():
    if "password_correct" not in st.session_state:
        st.session_state.password_correct = False
    
    if st.session_state.password_correct:
        return True

    st.subheader("🔒 Log in om toegang te krijgen")
    pwd = st.text_input("Wachtwoord:", type="password")
    if st.button("Inloggen"):
        if pwd == PASSWORD:
            st.session_state.password_correct = True
            st.rerun()
        else:
            st.error("Wachtwoord onjuist")
    return False

if not check_password():
    st.stop()

# API-key ophalen en configureren
api_key = st.secrets.get("GEMINI_API_KEY")
if not api_key:
    st.error("Voeg je API key toe in de Streamlit Secrets instellingen!")
    st.stop()

genai.configure(api_key=api_key)

# PDF's automatisch uitlezen uit de map
@st.cache_data
def get_pdf_texts():
    all_text = ""
    for file in os.listdir("."):
        if file.endswith(".pdf"):
            reader = PdfReader(file)
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    all_text += text + "\n"
    return all_text

with st.spinner("Acceptatiegidsen worden ingelezen..."):
    pdf_context = get_pdf_texts()

# Chatgeschiedenis
if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Stel je vraag over het acceptatiebeleid..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Even zoeken in de gidsen..."):
            try:
                # Gebruik het standaard stabiele flash-model
                model = genai.GenerativeModel("gemini-1.5-flash")
                
                full_prompt = f"Je bent een handige hypotheek assistent. Beantwoord de vraag uitsluitend op basis van de volgende acceptatiedocumentatie:\n\n{pdf_context[:100000]}\n\nVraag: {prompt}"
                
                response = model.generate_content(full_prompt)
                answer = response.text
            except Exception as e:
                answer = f"Er is een fout opgetreden: {e}"
                
            st.markdown(answer)
            st.session_state.messages.append({"role": "assistant", "content": answer})
