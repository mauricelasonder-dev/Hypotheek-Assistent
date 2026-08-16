import streamlit as st
import os
from langchain.chains import ConversationalRetrievalChain
from langchain_community.document_loaders import PyPDFDirectoryLoader
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain.text_splitter import RecursiveCharacterTextSplitter

# Pagina instellingen
st.set_page_config(page_title="Hypotheek Acceptatie Assistent", page_icon="🏠")

st.title("🏠 Acceptatiebeleid Assistent")

# Wachtwoord beveiliging
PASSWORD = "jouw-wachtwoord-hier" # Pas dit aan naar je eigen gekozen wachtwoord

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

# API-key ophalen uit Streamlit Secrets
api_key = st.secrets.get("OPENAI_API_KEY")
if not api_key:
    st.error("Voeg je API key toe in de Streamlit Secrets instellingen!")
    st.stop()

# PDF's inladen en doorzoekbaar maken
@st.cache_resource
def load_documents():
    # Zoekt in de map naar PDF's
    loader = PyPDFDirectoryLoader(".")
    documents = loader.load()
    
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    texts = text_splitter.split_documents(documents)
    
    embeddings = OpenAIEmbeddings(openai_api_key=api_key)
    vectorstore = Chroma.from_documents(texts, embeddings)
    return vectorstore.as_retriever(search_kwargs={"k": 3})

with st.spinner("Acceptatiegidsen worden geladen en doorzoekbaar gemaakt... Dit gebeurt eenmalig."):
    try:
        retriever = load_documents()
    except Exception as e:
        st.error(f"Fout bij laden van PDF's: {e}")
        st.stop()

# Chatgeheugen initialiseren
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

llm = ChatOpenAI(temperature=0, openai_api_key=api_key, model_name="gpt-4o-mini")
qa_chain = ConversationalRetrievalChain.from_llm(llm, retriever=retriever, return_source_documents=True)

# Vraag invoeren
user_query = st.chat_input("Stel je vraag over het acceptatiebeleid...")

if user_query:
    st.session_state.chat_history.append((user_query, ""))
    with st.spinner("Even zoeken in de gidsen..."):
        result = qa_chain({"question": user_query, "chat_history": st.session_state.chat_history[:-1]})
        answer = result["answer"]
        st.session_state.chat_history[-1] = (user_query, answer)

# Toon chatgeschiedenis
for query, response in st.session_state.chat_history:
    with st.chat_message("user"):
        st.write(query)
    with st.chat_message("assistant"):
        st.write(response)
