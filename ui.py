import streamlit as st
import asyncio

from main import run_multi_agent

st.set_page_config(
    page_title="Multi Agent Assistant",
    layout="centered"
)

st.title("🤖 Multi Agent AI Assistant -test1")

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:

    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

prompt = st.chat_input("Ask something...")

if prompt:

    st.session_state.messages.append(
        {
            "role": "user",
            "content": prompt
        }
    )

    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):

        with st.spinner("Thinking..."):

            response = asyncio.run(
                run_multi_agent(prompt)
            )

            st.markdown(response)

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": response
        }
    )