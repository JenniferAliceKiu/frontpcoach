import streamlit as st
import requests
from params import *

def send_to_llm_backend(message, session_id=None):
    payload = {"message": message}
    if session_id:
        payload["session_id"] = session_id
    try:
        resp = requests.post(API_URL, json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        reply = data.get("llm_response", "")
        sentiment = data.get("sentiment")
        return reply, sentiment
    except Exception as e:
        st.error(f"Error: {e}")
        return "Sorry, I couldn't reach the server.", None

def transcribe_audio_to_backend(audio_data, filename):
    files = {"audio_file": (filename, audio_data, "audio/wav")}
    response = requests.post("http://localhost:8000/transcribe-audio/", files=files)
    try:
        return response.json()
    except Exception:
        print("Backend response text:", response.text)
        print("Status code:", response.status_code)
        raise

def fetch_history(session_id):
    try:
        resp = requests.get(f"http://localhost:8000/chat/{session_id}/history", timeout=10)
        resp.raise_for_status()
        data = resp.json()
        # Convert backend format to frontend format
        history = data.get("history", [])
        messages = []
        for entry in history:
            role = entry.get("role", "assistant")
            content = entry.get("content", "")
            messages.append({"role": role, "content": content})
        return messages
    except Exception as e:
        st.warning(f"Could not load previous chat history: {e}")
        return []

def login():
    st.title("Login")
    username = st.text_input("Enter your username")
    if st.button("Login"):
        if username:
            try:
                # Only send username
                resp = requests.post(LOGIN_URL, json={"username": username}, timeout=10)
                resp.raise_for_status()
                data = resp.json()
                session_id = data.get("session_id")
                st.session_state.username = username
                st.session_state.session_id = session_id
                st.success("Login successful!")
                st.rerun()
            except Exception as e:
                st.error(f"Login failed: {e}")
        else:
            st.warning("Please enter a username.")
