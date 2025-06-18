import streamlit as st
import requests
from datetime import datetime
from audio_recorder_streamlit import audio_recorder
from params import *

URL = API_URL


def send_to_llm_backend(message, session_id=None):
    payload = {"message": message}
    if session_id:
        payload["session_id"] = session_id
    try:
        resp = requests.post(f"{URL}/chat", json=payload, timeout=60)
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
    response = requests.post(f"{URL}/transcribe-audio/", files=files)
    try:
        return response.json()
    except Exception:
        print("Backend response text:", response.text)
        print("Status code:", response.status_code)
        raise

def fetch_history(session_id):
    try:
        resp = requests.get(f"{URL}/chat/{session_id}/history", timeout=10)
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
                resp = requests.post(f"{URL}/login", json={"username": username}, timeout=10)
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


st.set_page_config(page_title="Therapist Chat", page_icon="💬")


if "username" not in st.session_state:
    login()
    st.stop()

# --- Initialize chat history ---
if "messages" not in st.session_state:
    if "session_id" in st.session_state and st.session_state.session_id:
        st.session_state.messages = fetch_history(st.session_state.session_id)
    else:
        st.session_state.messages = []


st.title("Therapist Chat")
st.write(f"Logged in as: {st.session_state.username}")


with st.sidebar:
    st.title("Audio Recorder")
    audio_file = audio_recorder(sample_rate=16_000)


transcription = None

if audio_file:
    if st.sidebar.button("Transcribe Recording", key="transcribe_recording_sidebar"):
        filename = f"recording_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav"
        result = transcribe_audio_to_backend(audio_file, filename)
        transcription = result.get('transcription')[0]['text']

        if transcription:
            # Add transcription as user message
            st.session_state.messages.append({"role": "user", "content": transcription})

            # --- Send to LLM backend and display response ---
            with st.spinner("Therapist is thinking..."):
                reply, sentiment = send_to_llm_backend(transcription, st.session_state.session_id)
            st.session_state.messages.append({"role": "assistant", "content": reply})
            if sentiment:
                label = sentiment.get("label", "")
                score = sentiment.get("score", 0.0)
                st.chat_message("assistant").write(f"*Sentiment: {label} ({score:.1%})*")

# Display the chat history
for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

# Input area
if user_input := st.chat_input("Your message..."):
    st.session_state.messages.append({"role": "user", "content": user_input})
    st.chat_message("user").write(user_input)

    payload = {"message": user_input}
    if st.session_state.session_id:
        payload["session_id"] = st.session_state.session_id

    with st.spinner("Therapist is thinking..."):
        try:
            resp = requests.post(f"{URL}/chat", json=payload, timeout=60)
            resp.raise_for_status()
            data = resp.json()
            new_sid = data.get("session_id", None)
            if new_sid and new_sid != st.session_state.session_id:
                st.session_state.session_id = new_sid
                st.query_params = {"session_id": [new_sid]}

            reply = data.get("llm_response", "")
            sentiment = data.get("sentiment")
        except Exception as e:
            st.error(f"Error: {e}")
            reply = "Sorry, I couldn't reach the server."
            sentiment = None

    if sentiment:
        label = sentiment.get("label", "")
        score = sentiment.get("score", 0.0)
        st.chat_message("assistant").write(f"*Sentiment: {label} ({score:.1%})*")

    st.session_state.messages.append({"role": "assistant", "content": reply})
    st.chat_message("assistant").write(reply)
