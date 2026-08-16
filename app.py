import streamlit as st
import os

# Pagina instellingen
st.set_page_config(page_title="Hypotheek Acceptatie Assistent", page_icon="🏠")

st.title("🏠 Acceptatiebeleid Assistent")

# Wachtwoord beveiliging
PASSWORD = "jouw-wachtwoord-hier" # Verander dit in een wachtwoord naar keuze

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

# Hier komt straks de logica voor je PDF's
st.success("Je bent ingelogd! De assistent is klaar voor je vragen.")
st.write("Tip: Je acceptatiegidsen worden in de volgende stap gekoppeld aan de AI.")