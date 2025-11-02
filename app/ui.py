import streamlit as st
import requests
from loguru import logger

# CONFIG

API_URL = "http://127.0.0.1:8000/ask"

st.set_page_config(page_title="Jarvis AI Agent", page_icon="🤖", layout="wide")

# SIDEBAR
st.sidebar.title("⚙️ Settings")
api_url = st.sidebar.text_input("API Endpoint", API_URL)
max_results = st.sidebar.slider("Search Depth", 1, 10, 3)
st.sidebar.markdown("---")
st.sidebar.caption("🧠 Powered by OpenRouter + FastAPI + Streamlit")

# MAIN UI
st.title("🤖 Jarvis — Autonomous AI Agent")
st.caption("Web Search + Memory + Reflection + Cache + UI")

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

prompt = st.text_area("Enter your query", placeholder="Ask Jarvis ..", height=100)

if st.button("Ask Jarvis 🚀"):
    if not prompt.strip():
        st.warning("Please enter a question first.")
    else:
        with st.spinner("Thinking..."):
            try:
                response = requests.post(api_url, json={"prompt": prompt})
                data = response.json()

                answer = data.get("response", "⚠️ No response.")
                cached = data.get("cached", False)
                memories = data.get("related_memories", [])

                st.session_state.chat_history.append({"user": prompt, "agent": answer})

                st.success("✅ Response Ready")
                st.markdown(f"### 🧩 Jarvis Says:")
                st.write(answer)

                if cached:
                    st.info("⚡ Response fetched from cache.")
                if memories:
                    with st.expander("📚 Related Memories"):
                        st.write(memories)

            except Exception as e:
                st.error(f"Error: {e}")
                logger.error(f"UI Error: {e}")

# CHAT HISTORY
if st.session_state.chat_history:
    st.markdown("---")
    st.subheader("💾 Conversation History")
    for chat in reversed(st.session_state.chat_history):
        st.markdown(f"**You:** {chat['user']}")
        st.markdown(f"**Jarvis:** {chat['agent']}")
        st.markdown("---")

