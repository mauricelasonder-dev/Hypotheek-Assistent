import streamlit as st
import os
from pypdf import PdfReader
from openai import OpenAI

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

# API-key ophalen (Gemini via OpenAI-compatibiliteit of rechtstreeks)
api_key = st.secrets.get("GEMINI_API_KEY") or st.secrets.get("OPENAI_API_KEY")
if not api_key:
    st.error("Voeg je API key toe in de Streamlit Secrets instellingen!")
    st.stop()

# We gebruiken Google's OpenAI-compatibel eindpunt zodat je je Gemini sleutel kunt gebruiken!
client = OpenAI(
    api_key=api_key,
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
)

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
            response = client.chat.completions.create(
                model="gemini-2.5-flash",
                messages=[
                    {"role": "system", "content": f"Je bent een handige hypotheek assistent. Beantwoord de vraag uitsluitend op basis van de volgende documentatie:\n\n{pdf_context[:100000]}"},
                    {"role": "user", "content": prompt}
                ]
            )
            answer = response.choices[0].message.content
            st.markdown(answer)
            st.session_state.messages.append({"role": "assistant", "content": answer})
