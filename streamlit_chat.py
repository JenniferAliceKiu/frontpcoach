import streamlit as st
import requests
from datetime import datetime
from audio_recorder_streamlit import audio_recorder
from params import *
from functions import send_to_llm_backend, transcribe_audio_to_backend, fetch_history, login

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
            resp = requests.post(API_URL, json=payload, timeout=60)
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
